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
import json
import os.path
from tool import FileUtil
from collections import OrderedDict

def start_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    options = plugin_context.options
    repositories = plugin_context.repositories
    cfg_url = plugin_context.get_variable('cfg_url', None)
    root_servers = {}
    clusters_cmd = {}
    if cluster_config.added_servers:
        scale_out = True
        need_bootstrap = False
    else:
        scale_out = False
        need_bootstrap = True

    scenario = cluster_config.get_global_conf_with_default().get('scenario')
    need_bootstrap and stdio.print('cluster scenario: %s' % scenario)
    for server in cluster_config.original_servers:
        config = cluster_config.get_server_conf(server)
        zone = config['zone']
        if zone not in root_servers:
            root_servers[zone] = '%s:%s:%s' % (server.ip, config['rpc_port'], config['mysql_port'])
    rs_list_opt = '-r \'%s\'' % ';'.join([root_servers[zone] for zone in root_servers])

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']

        if not server_config.get('data_dir'):
            server_config['data_dir'] = '%s/store' % home_path

        if client.execute_command('ls %s/clog/tenant_1/' % server_config['data_dir']).stdout.strip():
            need_bootstrap = False

        remote_pid_path = '%s/run/observer.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                continue

        stdio.verbose('%s start command construction' % server)
        if getattr(options, 'without_parameter', False) and client.execute_command('ls %s/etc/observer.config.bin' % home_path):
            use_parameter = False
        else:
            use_parameter = True
        cmd = []
        if use_parameter:
            not_opt_str = OrderedDict({
                'mysql_port': '-p',
                'rpc_port': '-P',
                'zone': '-z',
                'nodaemon': '-N',
                'appname': '-n',
                'cluster_id': '-c',
                'data_dir': '-d',
                'devname': '-i',
                'syslog_level': '-l',
                'ipv6': '-6',
                'mode': '-m',
                'scn': '-f',
                'local_ip': '-I'
            })
            not_cmd_opt = [
                'home_path', 'obconfig_url', 'root_password', 'proxyro_password', 'scenario',
                'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir', '$_zone_idc', 'production_mode',
                'ocp_monitor_tenant', 'ocp_monitor_username', 'ocp_monitor_password', 'ocp_monitor_db',
                'ocp_meta_tenant', 'ocp_meta_username', 'ocp_meta_password', 'ocp_meta_db', 'ocp_agent_monitor_password', 'ocp_root_password', 'obshell_port'
            ]
            get_value = lambda key: "'%s'" % server_config[key] if isinstance(server_config[key], str) else server_config[key]
            opt_str = []
            for key in server_config:
                if key not in not_cmd_opt and key not in not_opt_str and not key.startswith('ocp_meta_tenant_'):
                    value = get_value(key)
                    opt_str.append('%s=%s' % (key, value))
            if cfg_url:
                opt_str.append('obconfig_url=\'%s\'' % cfg_url)
            else:
                cmd.append(rs_list_opt)
            for key in not_opt_str:
                if key in server_config:
                    value = get_value(key)
                    cmd.append('%s %s' % (not_opt_str[key], value))
            cmd.append('-o %s' % ','.join(opt_str))
        else:
            cmd.append('-p %s' % server_config['mysql_port'])

        clusters_cmd[server] = 'cd %s; %s/bin/observer %s' % (home_path, home_path, ' '.join(cmd))

    plugin_context.set_variable('scale_out', scale_out)
    plugin_context.set_variable('need_bootstrap', need_bootstrap)
    plugin_context.set_variable('clusters_cmd', clusters_cmd)

    return plugin_context.return_true()
