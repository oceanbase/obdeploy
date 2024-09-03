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

import getpass
import os
from collections import defaultdict

import yaml
from  _mirror import get_use_centos_release
from _deploy import DeployStatus, DeployConfigStatus
from ssh import LocalClient
from _types import CapacityMB


stdio = None


def dump_yaml(config, config_yaml_path):
    os.makedirs(os.path.dirname(config_yaml_path), exist_ok=True)
    try:
        with open(config_yaml_path, 'w') as f:
            f.write(yaml.dump(dict(config), sort_keys=False))
            f.flush()
        return True
    except Exception as e:
        stdio.verbose(e)
        stdio.error('dump deploy info to %s failed' % config_yaml_path)
        return False


def get_global_key_value(ips_data):
    key_values_map = {}
    server_num = len(ips_data)
    for data in ips_data.values():
        for k, v in data.items():
            if k not in key_values_map:
                key_values_map[k] = [v, 1]
            elif key_values_map[k][0] == v:
                key_values_map[k][1] += 1
    common_key_values = {k: v[0] for k, v in key_values_map.items() if v[1] == server_num}
    return common_key_values


def exec_sql(sql, cursor, args=None, exec_type='fetchone', raise_exception=False, exc_level='error'):
    if exec_type == 'fetchall':
        return cursor.fetchall(sql, args=args, raise_exception=raise_exception, exc_level=exc_level) if cursor else False
    elif exec_type == 'fetchone':
        return cursor.fetchone(sql, args=args, raise_exception=raise_exception, exc_level=exc_level) if cursor else False
    else:
        return False
    

def format_server(ip, port):
    return '{}_{}'.format(ip, port)


def takeover(plugin_context, user_config={}, name='', obd_home='', *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if not value:
            value = default
        return value

    def error(msg):
        stdio.error(msg)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    options = plugin_context.options
    stdio = plugin_context.stdio
    stdio.start_loading('Takeover precheck')
    clients = plugin_context.clients
    cursor = kwargs.get('cursor')
    available_sql = "show databases"
    available = exec_sql(available_sql, cursor, exec_type='fetchone', raise_exception=False)
    if not available:
        stdio.error('The current OceanBase does not support takeover, the database is not available.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    check_ocs_sql = "show databases like 'ocs'"
    ocs = exec_sql(check_ocs_sql, cursor, exec_type='fetchone', raise_exception=True)
    if not ocs:
        stdio.error('The current OceanBase does not support takeover, OCS is not installed.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # check architecture
    check_ocs_sql = "select count(DISTINCT(architecture)) as count  from ocs.all_agent;"
    count = exec_sql(check_ocs_sql, cursor, exec_type='fetchone', raise_exception=True)
    if not count or count['count'] > 1:
        stdio.error('The current OceanBase does not support takeover, the architecture of the server is inconsistent.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # query all server hosts
    query_server_sql = "select ob.SVR_IP as ip, ob.SVR_PORT as rpc_port, ob.SQL_PORT as mysql_port, ob.ZONE as zone, ob.STATUS as status, ob.BUILD_VERSION as version, ocs.port as obshell_port, ocs.home_path as home_path  from oceanbase.DBA_OB_SERVERS as ob left join ocs.all_agent as ocs on ob.SVR_IP=ocs.ip and ob.SQL_PORT=ocs.mysql_port"
    servers = exec_sql(query_server_sql, cursor, exec_type='fetchall', raise_exception=True)
    version = None
    release = None
    dict_servers = {}
    bin_is_symbolic = False

    os_release_cmd = '''cat /etc/os-release  | grep '^VERSION_ID=' | awk -F '=' '{print $2}' | sed 's/"//g' | awk -F '.' '{print $1}' '''
    ret = LocalClient.execute_command(os_release_cmd, stdio=stdio)
    if not ret:
        error('Failed to get os version')
    os_release, _ = get_use_centos_release()
    for server in servers:
        if server['status'] != 'ACTIVE':
            return error('Server %s:%s is not active' % (server['ip'], server['mysql_port']))
        _version = server['version'].split('-')[0].split('_')[0]
        _release = server['version'].split('-')[0].split('_')[1]
        if version is None:
            version = _version
            release = '{}.el{}'.format(_release, os_release)
        else:
            if version != _version or release != '{}.el{}'.format(_release, os_release):
                return error('Server %s:%s version is not match' % (server['ip'], server['mysql_port']))

        home_path = server['home_path']
        for svr, client in clients.items():
            if server['ip'] == svr.ip:
                owner = client.execute_command("ls -ld %s/etc | awk '{print $3}'" % home_path).stdout.strip()
                if owner != client.config.username:
                    return error('Server {}:{} owner is not match. The SSH user for takeover does not match the owner that OceanBase is running under, SSH user: {}, expected: {}.'.format(server['ip'], server['mysql_port'], client.config.username, owner))
                bin_is_symbolic = client.execute_command('''[ -L "%s/bin/observer" ]''' % home_path).code == 0
                break

        ip = server['ip']
        rpc_port = server['rpc_port']
        del server['status']
        del server['version']
        del server['ip']

        dict_servers[format_server(ip, rpc_port)] = server
    stdio.stop_loading('succeed')

    stdio.start_loading('Generate config file')
    
    bool_parameter = {
        'enable_syslog_recycle': False,
        'enable_syslog_wf': True
    }
    int_parameter = {
        'log_disk_percentage': 0,
        'datafile_disk_percentage': 0,
        'cpu_count': 0,
        'max_syslog_file_count': 0,
        'memory_limit_percentage': 80,
        'cluster_id': 0
    }
    capacity_parameter = {
        'memory_limit': 0,
        'system_memory': 0,
        'log_disk_size': 0,
        'datafile_maxsize': 0,
        'datafile_size': 0,
        'datafile_next': 0
    }
    str_parameter = ['data_dir', 'cluster', 'devname']

    default_config = {}
    parameter_keys = [] + str_parameter
    for parameters in [bool_parameter, int_parameter, capacity_parameter]:
        parameter_keys += list(parameters.keys())
        default_config.update(parameters)

    query_parameter_sql = "show parameters where name in %s"
    parameters = exec_sql(query_parameter_sql, cursor, args=[parameter_keys], exec_type='fetchall', raise_exception=True)
    for parameter in parameters:
        key = parameter['name']
        default = ''
        if key in int_parameter:
            parameter['value'] = int(parameter['value'])
            default = int_parameter[key]
        elif key in bool_parameter:
            parameter['value'] = bool(parameter['value'])
            default = bool_parameter[key]
        elif key in capacity_parameter:
            parameter['value'] = CapacityMB(parameter['value']).value
            default = CapacityMB(capacity_parameter[key]).value

        if parameter['value'] == default:
            continue
        
        server = format_server(parameter['svr_ip'], parameter['svr_port'])
        dict_servers[server][key] = parameter['value']
    
    PRO_MEMORY_MIN = 16 << 30
    for server in dict_servers:
        config = dict_servers[server]
        if 'memory_limit' in config:
            dict_servers[server]['production_mode'] = CapacityMB(config['memory_limit']).bytes >= PRO_MEMORY_MIN
        if 'cluster' in config:
            config['appname'] = config['cluster']
            del config['cluster']

    config = defaultdict(dict)
    servers = []
    global_config = get_global_key_value(dict_servers)
    if user_config:
        config['user'] = user_config
    config['oceanbase-ce'] = {
        'version': version,
        'release': release,
        'servers': servers,
        'global': global_config
    }
    global_config['root_password'] = get_option('root_password', '')

    count = 1
    for server_ip_rpc_port, server_value in dict_servers.items():
        server_ip = server_ip_rpc_port.split('_')[0]
        server = dict()
        server['name'] = 'server{}'.format(count)
        server['ip'] = server_ip
        servers.append(server)
        server_config = dict()
        for key, value in server_value.items():
            if key not in global_config.keys():
                server_config[key] = value
        if server_config:
            config['oceanbase-ce']['server{}'.format(count)] = server_config
        count += 1
    stdio.verbose('dump config to file')
    config_yaml_path = '{}/cluster/{}/config.yaml'.format(obd_home, name)
    if not dump_yaml(config, config_yaml_path):
        return error('dump config to file failed')

    # dump .data file
    oceanbase_ce = dict()
    oceanbase_ce['version'] = version
    oceanbase_ce['release'] = release
    data = dict()
    data['name'] = name
    data['components'] = {'oceanbase-ce': oceanbase_ce}
    data['status'] = DeployStatus.STATUS_CONFIGURED.name
    data['config_status'] = DeployConfigStatus.UNCHNAGE.name
    data_file_path = '{}/cluster/{}/.data'.format(obd_home, name)
    if not dump_yaml(data, data_file_path):
        LocalClient.execute_command('rm -rf {}'.format(config_yaml_path))
        return error('dump .data file failed')

    # dump inner_config.yaml
    inner_config = dict()
    inner_config['oceanbase-ce'] = dict()
    for i in range(1, count):
        inner_config['oceanbase-ce']['servers{}'.format(i)] = dict()
    inner_config['$_deploy_install_mode'] = 'ln' if bin_is_symbolic else 'cp'
    inner_config_path = '{}/cluster/{}/inner_config.yaml'.format(obd_home, name)
    if not dump_yaml(inner_config, inner_config_path):
        LocalClient.execute_command('rm -rf {} {}'.format(config_yaml_path, data_file_path))
        return error('dump inner_config.yaml failed')

    stdio.stop_loading('succeed')
    plugin_context.return_true()
