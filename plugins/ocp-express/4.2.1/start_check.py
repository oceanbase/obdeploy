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

from copy import deepcopy
from _rpm import Version
import _errno as err
from _types import Capacity

success = True


def get_missing_required_parameters(parameters):
    results = []
    for key in ["jdbc_url", "jdbc_password", "jdbc_username", "cluster_name", "ob_cluster_id", "root_sys_password",
                "server_addresses", "agent_username", "agent_password"]:
        if parameters.get(key) is None:
            results.append(key)
    return results


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{udp*,tcp*}' | awk -F' ' '{if($4==\"0A\") print $2,$4,$10}' | grep ':%s' | awk -F' ' '{print $3}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    return res.stdout.strip().split('\n')


def password_check(passwd):
    pattern = r'''^(?=(.*[a-z]){2,})(?=(.*[A-Z]){2,})(?=(.*\d){2,})(?=(.*[~!@#%^&*_\-+=|(){}\[\]:;,.?/]){2,})[A-Za-z\d~!@#%^&*_\-+=|(){}\[\]:;,.?/]{8,32}$'''
    return True if re.match(pattern, passwd) else False


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


def prepare_parameters(cluster_config, stdio):
    # depends config
    env = {}
    depend_observer = False
    depend_info = {}
    ob_servers_conf = {}
    root_servers = []
    for comp in ["oceanbase", "oceanbase-ce"]:
        ob_zones = {}
        if comp in cluster_config.depends:
            depend_observer = True
            observer_globals = cluster_config.get_depend_config(comp)
            ocp_meta_keys = [
                "ocp_meta_tenant", "ocp_meta_db", "ocp_meta_username", "ocp_meta_password", "appname", "cluster_id", "root_password"
            ]
            for key in ocp_meta_keys:
                value = observer_globals.get(key)
                if value is not None:
                    depend_info[key] = value
            ob_servers = cluster_config.get_depend_servers(comp)
            connect_infos = []
            for ob_server in ob_servers:
                ob_servers_conf[ob_server] = ob_server_conf = cluster_config.get_depend_config(comp, ob_server)
                connect_infos.append([ob_server.ip, ob_server_conf['mysql_port']])
                zone = ob_server_conf['zone']
                if zone not in ob_zones:
                    ob_zones[zone] = ob_server
            depend_info['connect_infos'] = connect_infos
            root_servers = ob_zones.values()
            break
    for comp in ['obproxy', 'obproxy-ce']:
        if comp in cluster_config.depends:
            obproxy_servers = cluster_config.get_depend_servers(comp)
            obproxy_server = obproxy_servers[0]
            obproxy_server_config = cluster_config.get_depend_config(comp, obproxy_server)
            depend_info['server_ip'] = obproxy_server.ip
            depend_info['mysql_port'] = obproxy_server_config['listen_port']
            break
    if 'obagent' in cluster_config.depends:
        obagent_servers = cluster_config.get_depend_servers('obagent')
        server_addresses = []
        for obagent_server in obagent_servers:
            obagent_server_config_without_default = cluster_config.get_depend_config('obagent', obagent_server, with_default=False)
            obagent_server_config = cluster_config.get_depend_config('obagent', obagent_server)
            username = obagent_server_config['http_basic_auth_user']
            password = obagent_server_config['http_basic_auth_password']
            if 'obagent_username' not in depend_info:
                depend_info['obagent_username'] = username
            elif depend_info['obagent_username'] != username:
                stdio.error('The http basic auth of obagent is inconsistent')
                return
            if 'obagent_password' not in depend_info:
                depend_info['obagent_password'] = password
            elif depend_info['obagent_password'] != password:
                stdio.error('The http basic auth of obagent is inconsistent')
                return
            if obagent_server_config_without_default.get('sql_port'):
                sql_port = obagent_server_config['sql_port']
            elif ob_servers_conf.get(obagent_server) and ob_servers_conf[obagent_server].get('mysql_port'):
                sql_port = ob_servers_conf[obagent_server]['mysql_port']
            else:
                continue
            if obagent_server_config_without_default.get('rpc_port'):
                svr_port = obagent_server_config['rpc_port']
            elif ob_servers_conf.get(obagent_server) and ob_servers_conf[obagent_server].get('rpc_port'):
                svr_port = ob_servers_conf[obagent_server]['rpc_port']
            else:
                continue
            server_addresses.append({
                "address": obagent_server.ip,
                "svrPort": svr_port,
                "sqlPort": sql_port,
                "withRootServer": obagent_server in root_servers,
                "agentMgrPort": obagent_server_config.get('mgragent_http_port', 0),
                "agentMonPort": obagent_server_config.get('monagent_http_port', 0)
            })
        depend_info['server_addresses'] = server_addresses

    for server in cluster_config.servers:
        server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        original_server_config = cluster_config.get_original_server_conf(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                if depend_info.get('server_ip'):
                    server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'], depend_info['mysql_port'], depend_info['ocp_meta_db'])
                else:
                    server_config['connect_infos'] = depend_info.get('connect_infos')
                    server_config['ocp_meta_db'] = depend_info.get('ocp_meta_db')
                    server_config['jdbc_url'] = ''
            if 'jdbc_username' in missed_keys and depend_observer:
                server_config['jdbc_username'] = "{}@{}".format(depend_info['ocp_meta_username'], depend_info.get('ocp_meta_tenant', {}).get("tenant_name"))
            depends_key_maps = {
                "jdbc_password": "ocp_meta_password",
                "cluster_name": "appname",
                "ob_cluster_id": "cluster_id",
                "root_sys_password": "root_password",
                "agent_username": "obagent_username",
                "agent_password": "obagent_password",
                "server_addresses": "server_addresses"
            }
            for key in depends_key_maps:
                if key in missed_keys:
                    if depend_info.get(depends_key_maps[key]) is not None:
                        server_config[key] = depend_info[depends_key_maps[key]]
        env[server] = server_config
    return env


def start_check(plugin_context, init_check_status=False, work_dir_check=False, work_dir_empty_check=True, strict_check=False, precheck=False, 
                java_check=True, *args, **kwargs):
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
    option = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global success
    success = True

    check_status = {}
    plugin_context.set_variable('start_check_status', check_status)
    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
            'java': err.CheckStatus(),
            'disk': err.CheckStatus(),
            'mem': err.CheckStatus(),
            'oceanbase version': err.CheckStatus(),
            'obagent version': err.CheckStatus(),
            'admin_passwd': err.CheckStatus(),
        }
        if work_dir_check:
            check_status[server]['dir'] = err.CheckStatus()
    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.start_loading('Check before start ocp-express')
    env = prepare_parameters(cluster_config, stdio)
    if not env:
        return plugin_context.return_false()
    versions_check = {
        "oceanbase version": {
            'comps': ['oceanbase', 'oceanbase-ce'],
            'min_version': Version('4.0')
        },
        "obagent version": {
            'comps': ['obagent'],
            'min_version': Version('4.2.1')
        }
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
        server_config = env[server]
        missed_keys = get_missing_required_parameters(server_config)
        if missed_keys:
            stdio.error(err.EC_NEED_CONFIG.format(server=server, component=cluster_config.name, miss_keys=missed_keys))
            success = False
            continue
        home_path = server_config['home_path']
        if not precheck:
            remote_pid_path = '%s/run/ocp-express.pid' % home_path
            remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s' % remote_pid):
                    stdio.verbose('%s is running, skip' % server)
                    wait_2_pass()
                    continue

        if work_dir_check:
            ip = server.ip
            stdio.verbose('%s dir check' % server)
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]
            original_server_conf = cluster_config.get_server_conf(server)

            keys = ['home_path', 'log_dir']
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

                    if client.execute_command('bash -c "[ -a %s ]"' % path):
                        is_dir = client.execute_command('[ -d {} ]'.format(path))
                        has_write_permission = client.execute_command('[ -w {} ]'.format(path))
                        if is_dir and has_write_permission:
                            if empty_check:
                                ret = client.execute_command('ls %s' % path)
                                if not ret or ret.stdout.strip():
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
            continue
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
            continue
        check_pass('port')

    # java version check
    if java_check:
        for server in cluster_config.servers:
            client = clients[server]
            server_config = env[server]
            java_bin = server_config['java_bin']
            client.add_env('PATH', '%s/jre/bin:' % server_config['home_path'])
            ret = client.execute_command('{} -version'.format(java_bin))
            if not ret:
                critical('java', err.EC_OCP_EXPRESS_JAVA_NOT_FOUND.format(server=server), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0')])
                continue
            version_pattern = r'version\s+\"(\d+\.\d+.\d+)'
            found = re.search(version_pattern, ret.stdout) or re.search(version_pattern, ret.stderr)
            if not found:
                error('java', err.EC_OCP_EXPRESS_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'),])
                continue
            java_major_version = found.group(1)
            if Version(java_major_version) != Version('1.8.0'):
                critical('java', err.EC_OCP_EXPRESS_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'),])
                continue

    servers_memory = {}
    servers_disk = {}
    servers_client = {}
    ip_servers = {}

    for server in cluster_config.servers:
        client = clients[server]
        server_config = env[server]
        memory_size = Capacity(server_config['memory_size']).bytes
        if server_config.get('log_dir'):
            log_dir = server_config['log_dir']
        else:
            log_dir = os.path.join(server_config['home_path'], 'log')
        need_size = Capacity(server_config['logging_file_total_size_cap']).bytes
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
                    server_memory_stats[key] = Capacity(str(v)).bytes
            mem_suggests = [err.SUG_OCP_EXPRESS_REDUCE_MEM.format()]
            if memory_needed * 0.5 > server_memory_stats['available']:
                for server in ip_servers[ip]:
                    error('mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY_AVAILABLE.format(ip=ip, available=Capacity(server_memory_stats['available']), need=Capacity(memory_needed)), suggests=mem_suggests)
            elif memory_needed > server_memory_stats['free'] + server_memory_stats['buffers'] + server_memory_stats['cached']:
                for server in ip_servers[ip]:
                    error('mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY_CACHED.format(ip=ip, free=Capacity(server_memory_stats['free']), cached=Capacity(server_memory_stats['buffers'] + server_memory_stats['cached']), need=Capacity(memory_needed)), suggests=mem_suggests)
            elif memory_needed > server_memory_stats['free']:
                for server in ip_servers[ip]:
                    alert('mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY.format(ip=ip,  free=Capacity(server_memory_stats['free']), need=Capacity(memory_needed)), suggests=mem_suggests)
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
                        error('disk', err.EC_OCP_EXPRESS_NOT_ENOUGH_DISK.format(ip=ip, disk=mount_path, need=Capacity(disk_needed), avail=Capacity(disk_info[mount_path]['avail'])), suggests=[err.SUG_OCP_EXPRESS_REDUCE_DISK.format()])
        else:
            stdio.warn(err.WC_OCP_EXPRESS_FAILED_TO_GET_DISK_INFO.format(ip))

    # admin_passwd check
    for server in cluster_config.servers:
        server_config = env[server]
        admin_passwd = server_config.get('admin_passwd')
        if not admin_passwd or not password_check(admin_passwd):
            error('admin_passwd', err.EC_COMPONENT_PASSWD_ERROR.format(ip=server.ip, component='ocp-express', key='admin_passwd', rule='The password must be 8 to 32 characters in length, containing at least 2 uppercase letters, 2 lowercase letters, 2 numbers, and 2 of the following special characters: ~!@#%^&*_-+=|(){{}}[]:;,.?/'), suggests=[err.SUG_OCP_EXPRESS_EDIT_ADMIN_PASSWD.format()])

    plugin_context.set_variable('start_env', env)

    for server in cluster_config.servers:
        wait_2_pass()

    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
