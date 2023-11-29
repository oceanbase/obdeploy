# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function

import re
import os
import time
import datetime

from copy import deepcopy
from _rpm import Version
import _errno as err
from ssh import SshConfig, SshClient
from tool import Cursor
from const import CONST_OBD_HOME

success = True


def get_missing_required_parameters(parameters):
    results = []
    for key in ["jdbc_url", "jdbc_password", "jdbc_username"]:
        if parameters.get(key) is None:
            results.append(key)
    return results


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{udp*,tcp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    return res.stdout.strip().split('\n')


def password_check(passwd):
    pattern = r"((?=(.*\d){2,})(?=(.*[a-z]){2,})(?=(.*[A-Z]){2,})(?=(.*[~!@#%^&*_\-+=|(){}\[\]:;,.?/]){2,})[0-9a-zA-Z~!@#%^&*_\-+=|(){}\[\]:;,.?/]{8,32})"
    if re.match(pattern, passwd):
        return True


def parse_size(size):
    _bytes = 0
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1<<10, "M": 1<<20, "G": 1<<30, "T": 1<<40}
        match = re.match(r'(0|[1-9][0-9]*)\s*([B,K,M,G,T])', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def format_size(size, precision=1):
    units = ['B', 'K', 'M', 'G']
    units_num = len(units) - 1
    idx = 0
    if precision:
        div = 1024.0
        format = '%.' + str(precision) + 'f%s'
        limit = 1024
    else:
        div = 1024
        limit = 1024
        format = '%d%s'
    while idx < units_num and size >= limit:
        size /= div
        idx += 1
    return format % (size, units[idx])


def get_mount_path(disk, _path):
    _mount_path = '/'
    for p in disk:
        if p in _path:
            if len(p) > len(_mount_path):
                _mount_path = p
    return _mount_path


def get_disk_info_by_path(path, client, stdio):
    disk_info = {}
    ret = client.execute_command('df --block-size=1024 {}'.format(path))
    if ret:
        for total, used, avail, puse, path in re.findall(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(.+)', ret.stdout):
            disk_info[path] = {'total': int(total) << 10, 'avail': int(avail) << 10, 'need': 0}
            stdio.verbose('get disk info for path {}, total: {} avail: {}'.format(path, disk_info[path]['total'], disk_info[path]['avail']))
    return disk_info


def get_disk_info(all_paths, client, stdio):
    overview_ret = True
    disk_info = get_disk_info_by_path('', client, stdio)
    if not disk_info:
        overview_ret = False
        disk_info = get_disk_info_by_path('/', client, stdio)
        if not disk_info:
            disk_info['/'] = {'total': 0, 'avail': 0, 'need': 0}
    all_path_success = {}
    for path in all_paths:
        all_path_success[path] = False
        cur_path = path
        while cur_path not in disk_info:
            disk_info_for_current_path = get_disk_info_by_path(cur_path, client, stdio)
            if disk_info_for_current_path:
                disk_info.update(disk_info_for_current_path)
                all_path_success[path] = True
                break
            else:
                cur_path = os.path.dirname(cur_path)
    if overview_ret or all(all_path_success.values()):
        return disk_info


def get_ocp_depend_config(cluster_config, stdio):
    # depends config
    env = {}
    depend_observer = False
    depend_info = {}
    ob_servers_conf = {}
    for comp in ["oceanbase", "oceanbase-ce"]:
        ob_zones = {}
        if comp in cluster_config.depends:
            depend_observer = True
            ob_servers = cluster_config.get_depend_servers(comp)
            for ob_server in ob_servers:
                ob_servers_conf[ob_server] = ob_server_conf = cluster_config.get_depend_config(comp, ob_server)
                if 'server_ip' not in depend_info:
                    depend_info['server_ip'] = ob_server.ip
                    depend_info['mysql_port'] = ob_server_conf['mysql_port']
                    depend_info['root_password'] = ob_server_conf['root_password']
                zone = ob_server_conf['zone']
                if zone not in ob_zones:
                    ob_zones[zone] = ob_server
            break
    for comp in ['obproxy', 'obproxy-ce']:
        if comp in cluster_config.depends:
            obproxy_servers = cluster_config.get_depend_servers(comp)
            obproxy_server = obproxy_servers[0]
            obproxy_server_config = cluster_config.get_depend_config(comp, obproxy_server)
            depend_info['server_ip'] = obproxy_server.ip
            depend_info['mysql_port'] = obproxy_server_config['listen_port']
            break

    for server in cluster_config.servers:
        server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        original_server_config = cluster_config.get_original_server_conf(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'],
                                                                               depend_info['mysql_port'],
                                                                               server_config['ocp_meta_db'])
                server_config['jdbc_username'] = '%s@%s' % (
                server_config['ocp_meta_username'], server_config['ocp_meta_tenant']['tenant_name'])
                server_config['jdbc_password'] = server_config['ocp_meta_password']
                server_config['root_password'] = depend_info['root_password']
        env[server] = server_config
    return env


def execute_cmd(server_config, cmd):
    return cmd if not server_config.get('launch_user', None) else 'sudo ' + cmd


def start_check(plugin_context, init_check_status=False, work_dir_check=False, work_dir_empty_check=True, strict_check=False, precheck=False, *args, **kwargs):

    def check_pass(item):
        status = check_status[server]
        if status[item].status == err.CheckStatus.WAIT:
            status[item].status = err.CheckStatus.PASS
    def check_fail(item, error, suggests=[]):
        status = check_status[server][item]
        if status.status == err.CheckStatus.WAIT:
            status.error = error
            status.suggests = suggests
            status.status = err.CheckStatus.FAIL
    def wait_2_pass():
        status = check_status[server]
        for item in status:
            check_pass(item)
    def alert(item, error, suggests=[]):
        global success
        if strict_check:
            success = False
            check_fail(item, error, suggests)
            stdio.error(error)
        else:
            stdio.warn(error)
    def error(item, _error, suggests=[]):
        global success
        if plugin_context.dev_mode:
            stdio.warn(_error)
        else:
            success = False
            check_fail(item, _error, suggests)
            stdio.error(_error)
    def critical(item, error, suggests=[]):
        global success
        success = False
        check_fail(item, error, suggests)
        stdio.error(error)

    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global success
    success = True

    check_status = {}
    plugin_context.set_variable('start_check_status', check_status)
    for server in cluster_config.servers:
        check_status[server] = {
            'metadb connect': err.CheckStatus(),
            'port': err.CheckStatus(),
            'java': err.CheckStatus(),
            'disk': err.CheckStatus(),
            'mem': err.CheckStatus(),
            'oceanbase version': err.CheckStatus(),
            'time check': err.CheckStatus(),
            'launch user': err.CheckStatus(),
            'sudo nopasswd': err.CheckStatus(),
            'tenant': err.CheckStatus(),
            'clockdiff': err.CheckStatus()
        }
        if work_dir_check:
            check_status[server]['dir'] = err.CheckStatus()
    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.start_loading('Check before start ocp-server')
    env = get_ocp_depend_config(cluster_config, stdio)
    if not env:
        return plugin_context.return_false()

    if not cluster_config.depends:
        for server in cluster_config.servers:
            server_config = env[server]
            # check meta db connect before start
            jdbc_url = server_config['jdbc_url']
            jdbc_username = server_config['jdbc_username']
            jdbc_password = server_config['jdbc_password']
            root_password = server_config.get('root_password', '')
            matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
            cursor = getattr(options, 'metadb_cursor', '')
            cursor = kwargs.get('metadb_cursor', '') if cursor == '' else cursor
            stdio.verbose('metadb connect check')
            if matched:
                jdbc_host = matched.group(1)
                jdbc_port = matched.group(2)[1:]
                jdbc_database = matched.group(3)
                password = root_password if root_password else jdbc_password
                connected = False
                retries = 10
                while not connected and retries:
                    retries -= 1
                    try:
                        cursor = Cursor(ip=jdbc_host, port=jdbc_port, user=jdbc_username, password=jdbc_password,
                                        stdio=stdio)
                        connected = True
                    except:
                        jdbc_username = 'root'
                        time.sleep(1)
                if not connected:
                    success = False
                    error('metadb connect', err.EC_CONNECT_METADB, err.SUG_OCP_SERVER_JDBC_URL_CONFIG_ERROR)
                if cursor and not cursor.fetchone('show DATABASES like "%s"' % jdbc_database):
                    critical('metadb connect', err.EC_DB_NOT_IN_JDBC_URL, err.SUG_OCP_SERVER_JDBC_URL_CONFIG_ERROR)
            else:
                critical('metadb connect', err.EC_ERROR_JDBC_URL, err.SUG_OCP_SERVER_JDBC_URL_CONFIG_ERROR)
            client = clients[server]
            # time check
            stdio.verbose('time check ')
            now = client.execute_command('date +"%Y-%m-%d %H:%M:%S"').stdout.strip()
            now = datetime.datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
            stdio.verbose('now: %s' % now)
            stdio.verbose('cursor: %s' % cursor)
            if cursor:
                ob_time = cursor.fetchone("SELECT NOW() now")['now']
                stdio.verbose('ob_time: %s' % ob_time)
                if not abs((now - ob_time).total_seconds()) < 180:
                    critical('time check', err.EC_OCP_SERVER_TIME_SHIFT.format(server=server))

                # tenant check
                skip_create_tenant = 'False'
                skip_create_tenant = getattr(options, "skip_create_tenant", "False")
                if skip_create_tenant == 'False':
                    sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
                    meta_tenant = server_config.get('ocp_meta_tenant')['tenant_name']
                    meta_max_cpu = server_config['ocp_meta_tenant'].get('max_cpu', 2)
                    meta_memory_size = server_config['ocp_meta_tenant'].get('memory_size', '2G')
                    if server_config.get('ocp_monitor_tenant'):
                        monitor_user = server_config.get('ocp_monitor_username', 'monitor_user')
                        monitor_tenant = server_config['ocp_monitor_tenant']['tenant_name']
                        monitor_max_cpu = server_config['ocp_monitor_tenant'].get('max_cpu', 2)
                        monitor_memory_size = server_config['ocp_monitor_tenant'].get('memory_size', '4G')
                        res = cursor.fetchone(sql, [monitor_tenant])
                        if res:
                            error('tenant', err.EC_OCP_SERVER_TENANT_ALREADY_EXISTS.format({"tenant_name":monitor_tenant}))
                    res = cursor.fetchone(sql, [meta_tenant])
                    if res:
                        error('tenant', err.EC_OCP_SERVER_TENANT_ALREADY_EXISTS.format({"tenant_name":meta_tenant}))
                    break

    stdio.verbose('oceanbase version check')
    versions_check = {
        "oceanbase version": {
            'comps': ['oceanbase', 'oceanbase-ce'],
            'min_version': Version('4.0')
        },
    }
    repo_versions = {}
    for repository in plugin_context.repositories:
        repo_versions[repository.name] = repository.version

    for check_item in versions_check:
        for comp in versions_check[check_item]['comps']:
            if comp not in cluster_config.depends:
                continue
            depend_comp_version = repo_versions.get(comp)
            if depend_comp_version is None:
                stdio.verbose('failed to get {} version, skip version check'.format(comp))
                continue
            min_version = versions_check[check_item]['min_version']
            if depend_comp_version < min_version:
                critical(check_item, err.EC_OCP_EXPRESS_DEPENDS_COMP_VERSION.format(ocp_express_version=cluster_config.version, comp=comp, comp_version=min_version))

    server_port = {}
    servers_dirs = {}
    servers_check_dirs = {}
    for server in cluster_config.servers:
        client = clients[server]

        if not (client.execute_command('sudo -n true') or client.execute_command('[ `id -u` == "0" ]')):
            critical('sudo nopasswd', err.EC_SUDO_NOPASSWD.format(ip=str(server), user=client.config.username),
                     [err.SUG_SUDO_NOPASSWD.format(ip=str(server), user=client.config.username)])
        server_config = env[server]
        missed_keys = get_missing_required_parameters(server_config)
        if missed_keys:
            stdio.error(err.EC_NEED_CONFIG.format(server=server, component=cluster_config.name, miss_keys=missed_keys))
            success = False
        home_path = server_config['home_path']
        if not precheck:
            remote_pid_path = '%s/run/ocp-server.pid' % home_path
            remote_pid = client.execute_command(execute_cmd(server_config, 'cat %s' % remote_pid_path)).stdout.strip()
            if remote_pid:
                if client.execute_command(execute_cmd(server_config, 'ls /proc/%s' % remote_pid)):
                    stdio.verbose('%s is running, skip' % server)
                    wait_2_pass()

    # user check
    for server in cluster_config.servers:
        server_config = env[server]
        ocp_user = server_config.get('launch_user', '')
        if ocp_user:
            client = clients[server]
            if not client.execute_command(execute_cmd(server_config, "id -u %s" % ocp_user)):
                critical('launch user', err.EC_OCP_SERVER_LAUNCH_USER_NOT_EXIST.format(server=server, user=ocp_user))

    for server in cluster_config.servers:
        client = clients[server]
        server_config = env[server]
        if work_dir_check:
            ip = server.ip
            stdio.verbose('%s dir check' % server)
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]
            original_server_conf = cluster_config.get_server_conf(server)

            keys = ['home_path', 'log_dir', 'soft_dir']
            for key in keys:
                path = server_config.get(key)
                suggests = [err.SUG_CONFIG_CONFLICT_DIR.format(key=key, server=server)]
                if path in dirs and dirs[path]:
                    critical('dir', err.EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']), suggests)
                dirs[path] = {
                    'server': server,
                    'key': key,
                }
                if key not in original_server_conf:
                    continue
                empty_check = work_dir_empty_check
                while True:
                    if path in check_dirs:
                        if check_dirs[path] != True:
                            critical('dir', check_dirs[path], suggests)
                        break

                    if client.execute_command(execute_cmd(server_config, 'bash -c "[ -a %s ]"' % path)):
                        is_dir = client.execute_command(execute_cmd(server_config, '[ -d {} ]'.format(path)))
                        has_write_permission = client.execute_command(execute_cmd(server_config, '[ -w {} ]'.format(path)))
                        if is_dir and has_write_permission:
                            if empty_check:
                                check_privilege_cmd = "ls %s" % path
                                if server_config.get('launch_user', ''):
                                    check_privilege_cmd = "sudo su - %s -c 'ls %s'" % (server_config['launch_user'], path)
                                ret = client.execute_command(check_privilege_cmd)
                                if not ret:
                                    check_dirs[path] = err.EC_OCP_SERVER_DIR_ACCESS_FORBIDE.format(server=server, path=path, cur_path=path)
                                elif ret.stdout.strip():
                                    check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.NOT_EMPTY.format(path=path))
                                else:
                                    check_dirs[path] = True
                            else:
                                check_dirs[path] = True
                        else:
                            if not is_dir:
                                check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.NOT_DIR.format(path=path))
                            else:
                                check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=path))
                    else:
                        path = os.path.dirname(path)
                        empty_check = False

        port = server_config['port']
        ip = server.ip
        if ip not in server_port:
            server_port[ip] = {}
        ports = server_port[ip]
        if port in server_port[ip]:
            critical(
                'port',
                err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'],
                                                   key=ports[port]['key']),
                [err.SUG_PORT_CONFLICTS.format()]
            )
        ports[port] = {
            'server': server,
            'key': 'port'
        }
        if get_port_socket_inode(client, port):
            critical(
                'port',
                err.EC_CONFLICT_PORT.format(server=ip, port=port),
                [err.SUG_USE_OTHER_PORT.format()]
            )
        check_pass('port')

        try:
            # java version check
            java_bin = server_config.get('java_bin', '/usr/bin/java')
            ret = client.execute_command(execute_cmd(server_config, '{} -version'.format(java_bin)))
            stdio.verbose('java version %s' % ret)
            if not ret:
                critical('java', err.EC_OCP_EXPRESS_JAVA_NOT_FOUND.format(server=server), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0')])
            version_pattern = r'version\s+\"(\d+\.\d+\.\d+)(\_\d+)'
            found = re.search(version_pattern, ret.stdout) or re.search(version_pattern, ret.stderr)
            if not found:
                error('java', err.EC_OCP_EXPRESS_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'),])
            java_major_version = found.group(1)
            stdio.verbose('java_major_version %s' % java_major_version)
            java_update_version = found.group(2)[1:]
            stdio.verbose('java_update_version %s' % java_update_version)
            if Version(java_major_version) != Version('1.8.0') or int(java_update_version) < 161:
                critical('java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'),])
        except Exception as e:
            stdio.error(e)
            error('java', err.EC_OCP_EXPRESS_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'),
                  [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'), ])

        try:
            # clockdiff status check
            clockdiff_bin = 'which clockdiff'
            if client.execute_command(clockdiff_bin):
                check_pass('clockdiff')
            else:
                if not client.execute_command('sudo -n true'):
                    critical('clockdiff', err.EC_OCP_SERVER_CLOCKDIFF_NOT_EXISTS.format(server=server))
                ret = client.execute_command('sudo' + clockdiff_bin)
                if not ret:
                    critical('clockdiff', err.EC_OCP_SERVER_CLOCKDIFF_NOT_EXISTS.format(server=server))

                client.execute_command('which clockdiff | xargs sudo chmod u+s')
                client.execute_command("which clockdiff | xargs sudo setcap 'cap_net_raw+ep'")
        except Exception as e:
            stdio.error(e)
            critical('clockdiff', err.EC_OCP_SERVER_CLOCKDIFF_NOT_EXISTS.format(server=server))

    servers_memory = {}
    servers_disk = {}
    servers_client = {}
    ip_servers = {}

    for server in cluster_config.servers:
        client = clients[server]
        server_config = env[server]
        memory_size = parse_size(server_config.get('memory_size', '1G'))
        if server_config.get('log_dir'):
            log_dir = server_config['log_dir']
        else:
            log_dir = os.path.join(server_config['home_path'], 'log')
        need_size = parse_size(server_config.get('logging_file_total_size_cap', '1G'))
        ip = server.ip
        if ip not in servers_client:
            servers_client[ip] = client
        if ip not in servers_memory:
            servers_memory[ip] = {
                'need': memory_size,
                'server_num': 1
            }
        else:
            servers_memory[ip]['need'] += memory_size
            servers_memory[ip]['server_num'] += 1
        if ip not in servers_disk:
            servers_disk[ip] = {}
        if log_dir not in servers_disk[ip]:
            servers_disk[ip][log_dir] = need_size
        else:
            servers_disk[ip][log_dir] += need_size
        if ip not in ip_servers:
            ip_servers[ip] = [server]
        else:
            ip_servers[ip].append(server)
    # memory check
    for ip in servers_memory:
        client = servers_client[ip]
        memory_needed = servers_memory[ip]['need']
        ret = client.execute_command('cat /proc/meminfo')
        if ret:
            server_memory_stats = {}
            memory_key_map = {
                'MemTotal': 'total',
                'MemFree': 'free',
                'MemAvailable': 'available',
                'Buffers': 'buffers',
                'Cached': 'cached'
            }
            for key in memory_key_map:
                server_memory_stats[memory_key_map[key]] = 0

            for k, v in re.findall('(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
                if k in memory_key_map:
                    key = memory_key_map[k]
                    server_memory_stats[key] = parse_size(str(v))
            mem_suggests = [err.SUG_OCP_EXPRESS_REDUCE_MEM.format()]
            if memory_needed * 0.5 > server_memory_stats['available']:
                for server in ip_servers[ip]:
                    error('mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY_AVAILABLE.format(ip=ip, available=format_size(server_memory_stats['available']), need=format_size(memory_needed)), suggests=mem_suggests)
            elif memory_needed > server_memory_stats['free'] + server_memory_stats['buffers'] + server_memory_stats['cached']:
                for server in ip_servers[ip]:
                    error('mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY_CACHED.format(ip=ip, free=format_size(server_memory_stats['free']), cached=format_size(server_memory_stats['buffers'] + server_memory_stats['cached']), need=format_size(memory_needed)), suggests=mem_suggests)
            elif memory_needed > server_memory_stats['free']:
                for server in ip_servers[ip]:
                    alert('mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY.format(ip=ip,  free=format_size(server_memory_stats['free']), need=format_size(memory_needed)), suggests=mem_suggests)
    # disk check
    for ip in servers_disk:
        client = servers_client[ip]
        disk_info = get_disk_info(all_paths=servers_disk[ip], client=client, stdio=stdio)
        if disk_info:
            for path in servers_disk[ip]:
                disk_needed = servers_disk[ip][path]
                mount_path = get_mount_path(disk_info, path)
                if disk_needed > disk_info[mount_path]['avail']:
                    for server in ip_servers[ip]:
                        error('disk', err.EC_OCP_EXPRESS_NOT_ENOUGH_DISK.format(ip=ip, disk=mount_path, need=format_size(disk_needed), avail=format_size(disk_info[mount_path]['avail'])), suggests=[err.SUG_OCP_EXPRESS_REDUCE_DISK.format()])
        else:
            stdio.warn(err.WC_OCP_EXPRESS_FAILED_TO_GET_DISK_INFO.format(ip))
    plugin_context.set_variable('start_env', env)

    for server in cluster_config.servers:
        wait_2_pass()

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
