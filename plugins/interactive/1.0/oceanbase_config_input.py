# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import getpass
import os

import const
from _rpm import Version
from _stdio import FormatText
from _types import Capacity
from tool import port_check, ConfigUtil, get_system_memory, input_int_value, byte_to_GB


def oceanbase_config_input(plugin_context, client, cluster_name=None, *args, **kwargs):
    def dir_check(client, dir_path, create_dir=False, memory_limit=None):
        flag = False

        if not os.path.isabs(dir_path):
            stdio.print(FormatText.error("The directory must be an absolute path. Please try again."))
            flag = True

        dir_exists = client.execute_command(f"[ -d '{dir_path}' ] && echo true || echo false").stdout.strip() == "true"

        if dir_exists:
            is_empty = client.execute_command(
                f"[ -z \"$(ls -A '{dir_path}')\" ] && echo true || echo false").stdout.strip() == "true"
            if not is_empty:
                stdio.print(FormatText.error("The directory must be empty. Please choose an empty directory."))
                flag = True

            can_access = client.execute_command(
                f"[ -r '{dir_path}' ] && [ -w '{dir_path}' ] && echo true || echo false").stdout.strip() == "true"
            if not can_access:
                stdio.print(FormatText.error(
                    "The current user doesn't have read/write permissions for this directory. "
                    "Please choose a directory with the required access permissions."))
                flag = True
        else:
            parent_dir = dir_path
            while True:
                parent_dir = client.execute_command(
                    f"dir='{parent_dir}'; echo \"${{dir%/*}}\"").stdout.strip()

                parent_exists = client.execute_command(
                    f"[ -e '{parent_dir}' ] && echo true || echo false").stdout.strip() == "true"

                if not parent_exists:
                    if parent_dir == client.execute_command(
                            f"dir='{parent_dir}'; echo \"${{dir%/*}}\"").stdout.strip():
                        break
                    continue

                parent_accessible = client.execute_command(
                    f"[ -w '{parent_dir}' ] && [ -r '{parent_dir}' ] && echo true || echo false").stdout.strip() == "true"
                if not parent_accessible:
                    stdio.print(FormatText.error(
                        f"The current user doesn't have read/write permissions for the parent directory "
                        f"{parent_dir}. Please choose a directory with the required access permissions."))
                    flag = True
                break

        if create_dir and not flag:
            result = client.execute_command(f"mkdir -p '{dir_path}' && echo SUCCESS || echo FAILED").stdout
            if "SUCCESS" not in result:
                stdio.print(FormatText.error(f"Failed to create directory {dir_path}"))
                flag = True

            if memory_limit is not None and client.execute_command("ls %s" % dir_path):
                client.execute_command(f'mkdir -p {dir_path}')
                df_cmd = (
                        "df -k '" + dir_path + "' | tail -1 | awk '{print $4}'"
                )

                try:
                    avail_bytes = client.execute_command(df_cmd)
                    stdio.verbose(f"Available disk space: {avail_bytes.stdout.strip()}")
                    disk_available = int(avail_bytes.stdout.strip()) * 1024

                    if disk_available < 3 * memory_limit:
                        stdio.print(FormatText.warning(
                            "Insufficient disk space in the directory. For business purposes, "
                            f"OceanBase recommends that disk space should not be less than 3*memory limit "
                            f"({Capacity(memory_limit)})."))

                    if disk_available < 2 * memory_limit:
                        stdio.print(FormatText.error(
                            "Insufficient disk space in the directory. Please choose a directory with "
                            f"disk space greater than 2*memory limit ({Capacity(memory_limit)})."))
                        flag = True
                except (ValueError, AttributeError) as e:
                    stdio.print(FormatText.error(f"Failed to check disk space: {str(e)}"))
                    flag = True

        return not flag

    def check_same_filesystem(client, path1, path2):
        cmd = (
            f"df -P '{path1}' '{path2}' | "
            "awk 'NR==2 {a=$1} NR==3 {print a==$1}'"
        )
        result = client.execute_command(cmd).stdout.strip()
        return result == "1"

    stdio = plugin_context.stdio
    user = client.config.username
    mirror_manager = kwargs.get('mirror_manager')
    oceanbase_pkgs = dict()
    for comp in const.COMPS_OB:
        pkgs = mirror_manager.get_pkgs_info(name=comp)
        if pkgs:
            oceanbase_pkgs[comp] = pkgs

    if not oceanbase_pkgs:
        stdio.print(FormatText.error('No OceanBase packages found in the mirror.'))
        return plugin_context.return_false()

    oceanbase_options = dict()
    if len(oceanbase_pkgs) > 1:
        stdio.print(FormatText.warning('    Multiple OceanBase packages found in the mirror. Please choose one:'))
        index = 0
        for comp in oceanbase_pkgs.keys():
            index += 1
            oceanbase_options[str(index)] = comp
            stdio.print(f'    {index}) {comp + (" (Community)" if comp == const.COMP_OB_CE else " (Business)")}')
        while True:
            number = stdio.read('Enter the number of the oceanbase type you want to use: ', blocked=True).strip()
            if not number or not oceanbase_options.get(number):
                stdio.print(FormatText.error('Invalid number. Please try again.'))
                continue
            else:
                oceanbase_pkgs = oceanbase_pkgs[oceanbase_options[number]]
                break
    else:
        oceanbase_pkgs = list(oceanbase_pkgs.values())[0]

    oceanbase_pkgs = sorted(oceanbase_pkgs, key=lambda x: x, reverse=True)
    pkg_versions = []
    need_remove_pkgs = []
    for pkg in oceanbase_pkgs:
        if pkg.version not in pkg_versions:
            pkg_versions.append(pkg.version)
            continue
        else:
            need_remove_pkgs.append(pkg)
    for pkg in need_remove_pkgs:
        oceanbase_pkgs.remove(pkg)

    stdio.print_list(
        oceanbase_pkgs[:5] if len(oceanbase_pkgs) > 5 else oceanbase_pkgs,
        ['name', 'version', 'release', 'arch', 'md5'],
        lambda x: [x.name, x.version, x.release, x.arch, x.md5],
        title='Available Oceanbase'
    )
    if len(oceanbase_pkgs) > 5:
        stdio.print('......')

    oceanbase_pkg = oceanbase_pkgs[0]
    if len(oceanbase_pkgs) > 1:
        rv = stdio.confirm(FormatText.warning('Are you sure to deploy using this latest version(%s) of Oceanbase.: ' % oceanbase_pkg.version), default_option=True)
        if not rv:
            while True:
                version = stdio.read('Enter the version of %s you want to use (e.g.: %s): ' % (oceanbase_pkg.name, oceanbase_pkg.version), blocked=True).strip().lower()
                if not version:
                    stdio.print(FormatText.error('Invalid version. Please try again.'))
                    continue
                try:
                    new_oceanbase_pkg = mirror_manager.get_exact_pkg(name=oceanbase_pkg.name, version=Version(version))
                    if not new_oceanbase_pkg:
                        stdio.print(FormatText.error('No OceanBase packages found in the mirror. Please enter a valid version.'))
                        continue
                    stdio.print_list(
                        [new_oceanbase_pkg],
                        ['name', 'version', 'release', 'arch', 'md5'],
                        lambda x: [x.name, x.version, x.release, x.arch, x.md5],
                        title='Available Oceanbase'
                    )
                    oceanbase_pkg = new_oceanbase_pkg
                    break
                except Exception as e:
                    stdio.print(FormatText.error(e))
                    continue
    ports = []
    while True:
        mysql_port = stdio.read('Enter the OB SQL port (Default: 2881): ', blocked=True).strip() or 2881
        mysql_port = int(mysql_port)
        rv, ports = port_check(mysql_port, client, ports, stdio)
        if rv:
            break
        else:
            continue

    while True:
        rpc_port = stdio.read('Enter the OB RPC port (Default: 2882): ', blocked=True).strip() or 2882
        rpc_port = int(rpc_port)
        rv, ports = port_check(rpc_port, client, ports, stdio)
        if rv:
            break
        else:
            continue
    obshell_port = None
    if oceanbase_pkg.name in [const.COMP_OB_STANDALONE, const.COMP_OB_CE]:
        while True:
            obshell_port = stdio.read('Enter the obshell port (Default: 2886): ', blocked=True).strip() or 2886
            obshell_port = int(obshell_port)
            rv, ports = port_check(obshell_port, client, ports, stdio)
            if rv:
                break
            else:
                continue
    while True:
        default_root_password = ConfigUtil.get_random_pwd_by_total_length(20)
        root_password = getpass.getpass("Enter the OB root password (Default: %s): " % default_root_password).strip() or default_root_password
        if root_password == default_root_password:
            break
        root_password_second = getpass.getpass("Confirm the OB root password: ").strip()
        if root_password == root_password_second:
            break
        else:
            stdio.print(FormatText.error('The two passwords do not match. Please try again.'))
    while True:
        default_cpu_count = client.execute_command("grep -e 'processor\s*:' /proc/cpuinfo | wc -l").stdout.strip()
        cpu_count = stdio.read(f'Enter the OB cpu count (Default: {default_cpu_count}): ', blocked=True).strip() or default_cpu_count
        if not cpu_count.isdigit():
            stdio.print(FormatText.error('Invalid cpu count. Please try again.'))
            continue
        cpu_count = int(cpu_count)
        if cpu_count < 8:
            stdio.print(FormatText.warning('The cpu_count cannot be less than 8. It will be set to 8 automatically.'))
            cpu_count = 8
        break
    while True:
        memory_free = int(client.execute_command("free -g | grep Mem | awk '{print $7}'").stdout.strip())
        if memory_free < 6:
            stdio.error("The machine's minimum memory cannot be less than min_value (6G). Please try again.")
            return plugin_context.return_false()
        elif memory_free < 8:
            default_memory_limit = memory_free
        else:
            default_memory_limit = int(memory_free) - 1
        memory_limit = stdio.read(f'Enter the OB memory limit (Configurable Range[6, {default_memory_limit}]， Default: {default_memory_limit}, Unit: G): ', blocked=True).strip() or default_memory_limit
        memory_limit = str(memory_limit)
        if not memory_limit.isdigit():
            stdio.print(FormatText.error("Invalid memory limit. Only digits are allowed. Please try again."))
            continue
        memory_limit = int(memory_limit)
        if memory_limit < 6:
            stdio.print(FormatText.error(" The machine's minimum memory cannot be less than min_value (6G). Please try again."))
            continue
        if memory_limit > default_memory_limit:
            stdio.print(FormatText.error(" The machine's maximum memory cannot be greater than max_value (default_memory_limit). Please try again."))
            continue
        memory_limit = Capacity(str(memory_limit) + 'G').bytes
        break
    while True:
        if user == 'root':
            default_home_path = f'/{user}/{cluster_name}'
        else:
            default_home_path = f'/home/{user}/{cluster_name}'
        home_path = stdio.read(f'Enter the OB installation directory (Default: {default_home_path}): ', blocked=True).strip() or default_home_path
        if dir_check(client, home_path, create_dir=False, memory_limit=memory_limit):
            client.execute_command(f'mkdir -p {home_path}')
            break
    while True:
        data_dir = stdio.read(f'Enter the OB data directory (Default: /data/1/{cluster_name}): ', blocked=True).strip() or f'/data/1/{cluster_name}'
        if dir_check(client, data_dir, create_dir=True, memory_limit=memory_limit):
            break
    while True:
        log_dir = stdio.read(f'Enter the OB log directory (Default: /data/log1/{cluster_name}): ', blocked=True).strip() or f'/data/log1/{cluster_name}'
        if dir_check(client, log_dir, create_dir=True, memory_limit=memory_limit):
            break

    scenario = None
    while True:
        if oceanbase_pkg.version < Version('4.2.5.0'):
            break
        scenarios = ['express_oltp', 'complex_oltp', 'olap', 'htap', 'kv']
        scenario_check = lambda scenario: scenario in scenarios
        optzs = {
            '1': 'express_oltp',
            '2': 'complex_oltp',
            '3': 'olap',
            '4': 'htap',
            '5': 'kv',
        }
        stdio.print("Cluster optimization scenario not specified, please specify the scenario you want to optimize.")
        default_key = '1'
        for k, v in optzs.items():
            if v == 'htap':
                default_key = k
                stdio.print("%s. %s (default)" % (k, v))
            else:
                stdio.print("%s. %s" % (k, v))
        optz = stdio.read('Please input the scenario you want to optimize [default: %s]: ' % default_key, blocked=True).strip().lower()
        if not optz:
            scenario = 'htap'
        elif optz in optzs:
            scenario = optzs[optz]
        elif scenario_check(optz):
            scenario = optz
        else:
            stdio.print(FormatText.error('Invalid input, please input again.'))
            continue
        break

    same_disk = False

    if check_same_filesystem(client, data_dir, log_dir):
        stdio.print(FormatText.warning('The data_dir and redo_dir are using the same disk.'))
        same_disk = True

    clog_size = Capacity('4G').bytes
    slog_size = Capacity('4G').bytes
    system_memory = get_system_memory(memory_limit)

    if same_disk:
        all_disk_free = Capacity(
            client.execute_command(f"df -BG {data_dir} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes
        disk_free = all_disk_free * 0.9 - slog_size - clog_size
        default_log_disk_size = 3 * memory_limit - 2 * system_memory
        double_memory_limit = 2 * memory_limit
        if disk_free < 2 * double_memory_limit:
            stdio.error(f'The disk space is not enough, please check the data_dir and log_dir.(need: {str(Capacity(2 * double_memory_limit))}, available: {str(Capacity(disk_free))})')
            return plugin_context.return_false()

        # log_disk_size
        log_disk_size = Capacity(str(input_int_value('log disk size', byte_to_GB(double_memory_limit), byte_to_GB(default_log_disk_size), default_value=byte_to_GB(default_log_disk_size), stdio=stdio)) + 'G').bytes

        # datafile_maxsize with G
        if disk_free - log_disk_size < double_memory_limit:
            stdio.error(f'The disk space is not enough, please check the data_dir and log_dir.(need: {str(Capacity(double_memory_limit))}, available: {str(Capacity(disk_free - log_disk_size))})')
            return plugin_context.return_false()
        max_available_datasize = byte_to_GB(disk_free - log_disk_size)
        datafile_maxsize = Capacity(str(input_int_value('datafile maxsize', byte_to_GB(double_memory_limit), max_available_datasize, default_value=max_available_datasize, stdio=stdio)) + 'G').bytes

    else:
        # log disk size
        log_disk_free = Capacity(
            client.execute_command(f"df -BG {log_dir} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes * 0.9
        if log_disk_free < 2 * memory_limit:
            stdio.error(f'The disk space is not enough, please check the log_dir.(need: {str(Capacity(2 * memory_limit))}, available: {str(Capacity(log_disk_free))})')
            return plugin_context.return_false()
        default_log_disk_size = min(3 * memory_limit - 2 * system_memory, log_disk_free)
        log_disk_size = Capacity(str(input_int_value('log disk size', byte_to_GB(2 * memory_limit), byte_to_GB(default_log_disk_size), default_value=byte_to_GB(default_log_disk_size), stdio=stdio)) + 'G').bytes

        # datafile_maxsize
        data_disk_free = Capacity(client.execute_command(
            f"df -BG {log_dir} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes * 0.9 - slog_size - clog_size
        if data_disk_free < 2 * memory_limit:
            stdio.error(f'The disk space is not enough, please check the data_dir.(need: {str(Capacity(2 * memory_limit))}, available: {str(Capacity(log_disk_free))})')
            return plugin_context.return_false()
        datafile_maxsize = Capacity(str(input_int_value('datafile maxsize', byte_to_GB(2 * memory_limit), byte_to_GB(data_disk_free), default_value=byte_to_GB(data_disk_free), stdio=stdio)) + 'G').bytes
    
    oceanbase_config = {
        "name": oceanbase_pkg.name,
        'version': str(oceanbase_pkg.version),
        'release': str(oceanbase_pkg.release),
        'mysql_port': mysql_port,
        'rpc_port': rpc_port,
        'obshell_port': obshell_port,
        'root_password': root_password,
        'cpu_count': cpu_count,
        'memory_limit': memory_limit,
        'home_path': f'{home_path}',
        'data_dir': data_dir,
        'log_dir': log_dir,
        'datafile_maxsize': datafile_maxsize,
        'log_disk_size': log_disk_size,
        'scenario': scenario,
    }
    plugin_context.set_variable('ports', ports)
    plugin_context.set_variable('oceanbase_config', oceanbase_config)
    return plugin_context.return_true(oceanbase_config=oceanbase_config)