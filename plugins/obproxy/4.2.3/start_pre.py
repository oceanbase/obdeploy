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

import hashlib


def start_pre(plugin_context, need_bootstrap=False, *args, **kwargs):
    new_cluster_config = kwargs.get('new_cluster_config')
    cluster_config = new_cluster_config if new_cluster_config else plugin_context.cluster_config
    clients = plugin_context.clients
    options = plugin_context.options
    clusters_cmd = {}
    real_cmd = {}
    pid_path = {}
    obproxy_config_server_url = plugin_context.get_variable('obproxy_config_server_url')

    if not getattr(options, 'with_parameter', False):
        use_parameter = False
    else:
        # Bootstrap is required when starting with parameter, ensure the passwords are correct.
        need_bootstrap = True
        use_parameter = True

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        if not server_config.get('obproxy_config_server_url') and obproxy_config_server_url:
            server_config['obproxy_config_server_url'] = obproxy_config_server_url

        if not client.execute_command('ls %s/etc/obproxy_config.bin' % home_path):
            need_bootstrap = True

        pid_path[server] = "%s/run/obproxy-%s-%s.pid" % (home_path, server.ip, server_config["listen_port"])

        start_parameters = {}
        if new_cluster_config:
            old_config = plugin_context.cluster_config.get_server_conf_with_default(server)
            new_config = new_cluster_config.get_server_conf_with_default(server)
            for key in new_config:
                param_value = new_config[key]
                if key not in old_config or old_config[key] != param_value:
                    start_parameters[key] = param_value
        else:
            start_parameters = server_config
        
        if use_parameter:
            not_opt_str = [
                'listen_port',
                'prometheus_listen_port',
                'rs_list',
                'cluster_name'
            ]
            start_unuse = ['home_path', 'observer_sys_password', 'obproxy_sys_password', 'observer_root_password']
            get_value = lambda key: "'%s'" % start_parameters[key] if isinstance(start_parameters[key], str) else \
            start_parameters[key]
            opt_str = []
            if not new_cluster_config:
                if start_parameters.get('obproxy_sys_password'):
                    obproxy_sys_password = hashlib.sha1(start_parameters['obproxy_sys_password'].encode("utf-8")).hexdigest()
                else:
                    obproxy_sys_password = ''
                if start_parameters.get('proxy_id'):
                    opt_str.append("client_session_id_version=%s,proxy_id=%s" % (start_parameters.get('client_session_id_version', 2), start_parameters.get('proxy_id')))
                opt_str.append("obproxy_sys_password='%s'" % obproxy_sys_password)
            for key in start_parameters:
                if key not in start_unuse and key not in not_opt_str:
                    value = get_value(key)
                    opt_str.append('%s=%s' % (key, value))
            cmd = ['-o %s' % ','.join(opt_str)]
            start_parameters['listen_port'] = server_config['listen_port']
            for key in not_opt_str:
                if key in start_parameters:
                    value = get_value(key)
                    cmd.append('--%s %s' % (key, value))
        else:
            cmd = ['--listen_port %s' % start_parameters.get('listen_port')]

        real_cmd[server] = '%s/bin/obproxy %s' % (home_path, ' '.join(cmd))
        clusters_cmd[server] = 'cd %s; %s' % (home_path, real_cmd[server])
    plugin_context.set_variable('clusters_cmd', clusters_cmd)
    plugin_context.set_variable('real_cmd', real_cmd)
    plugin_context.set_variable('need_bootstrap', need_bootstrap)
    plugin_context.set_variable('pid_path', pid_path)

    return plugin_context.return_true()

