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

import os
import bcrypt

from tool import YamlLoader
from copy import deepcopy

def hashed_with_bcrypt(content):
    content_bytes = content.encode('utf-8')
    hash_str = bcrypt.hashpw(content_bytes, bcrypt.gensalt())
    return hash_str.decode()

def start_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    cluster_receivers_conf = cluster_config.get_receivers_conf()
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    options = plugin_context.options
    invalid_keys = ["web.listen-address", "storage.path", "data.retention", "web.config.file"]
    yaml = YamlLoader(stdio=stdio)
    cmd_args_map = {}

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        runtime_alertmanager_conf = os.path.join(home_path, 'alertmanager.yaml')
        alertmanager_customize_config = server_config.get('alertmanager_config', {})
        port = server_config['port']
        address = server_config['address']
        data_dir = server_config.get('data_dir', os.path.join(home_path, 'data'))

        flag_file = os.path.join(home_path, '.alertmanager_started')
        if getattr(options, 'without_parameter', False) and client.execute_command('ls %s' % flag_file):
            use_parameter = False
        else:
            use_parameter = True 

        remote_pid_path = os.path.join(home_path, 'run/alertmanager.pid')
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            stdio.verbose('%s is runnning in %s, skip' % (server, remote_pid))
            continue       

        if use_parameter:
            if alertmanager_customize_config:
                config_tenant = yaml.dumps(alertmanager_customize_config).strip()
                if not client.write_file(config_tenant, runtime_alertmanager_conf):
                    stdio.error('failed to write config file {}'.format(runtime_alertmanager_conf))
                    return False
            else:
                receivers = server_config['receivers']
                receiver_list = []

                for index, receiver in enumerate(receivers):
                    if cluster_receivers_conf.get(receiver):
                        type_configs = {}
                        receiver_config = cluster_receivers_conf.get(receiver)
                        if 'receiver_type' in receiver_config:
                            notice_config = receiver_config['receiver_type']+'_configs'
                            type_configs = {
                                'name': receiver,
                                notice_config: [{k: v for k, v in receiver_config.items() if k != 'receiver_type'}]
                            }
                            receiver_list.append(type_configs)
                        else:
                            stdio.error(f"{receiver} notification type must be set")
                            return False
                    else:
                        stdio.error(f"The notification configuration of {receiver} must be set")
                        return False
                
                if len(receivers) == 1:
                    alertmanager_config = {
                        'route': {
                            'receiver': receivers[0]
                        },
                        'receivers': receiver_list
                    }
                else:
                    routes = []
                    for i, receiver in enumerate(receivers[1:], 1):
                        route_item = {'receiver': receiver}
                        if i < len(receivers) - 1:
                            route_item['continue'] = True
                        routes.append(route_item)
                    
                    alertmanager_config = {
                        'route': {
                            'receiver': receivers[0],
                            'routes': routes
                        },
                        'receivers': receiver_list
                    }

                config_tenant = yaml.dumps(alertmanager_config)
                if not client.write_file(config_tenant, runtime_alertmanager_conf):
                    stdio.error('failed to write config file {}'.format(runtime_alertmanager_conf))
                    return False
            client.execute_command('touch %s' % flag_file)
        
        cmd_items = ['--config.file={}'.format(runtime_alertmanager_conf)]
        cmd_items.append('--web.listen-address={}:{}'.format(address, port))
        cmd_items.append('--storage.path={}'.format(data_dir))
        cmd_items.append('--data.retention={}'.format(server_config['data_retention']))
        cmd_items.append('--cluster.listen-address=')

        basic_auth_users = deepcopy(server_config.get('basic_auth_users', {}))
        web_config = deepcopy(server_config.get('web_config', {}))
        if basic_auth_users or web_config:
            if 'basic_auth_users' in web_config:
                stdio.warn('{}: basic_auth_users do not work in web_config, please set basic_auth_users in configuration.'.format(server))
                return False
            try:
                for k, v in basic_auth_users.items():
                    basic_auth_users[str(k)] = hashed_with_bcrypt(str(v))
                web_config['basic_auth_users'] = basic_auth_users
                web_config_path = os.path.join(home_path, 'web_config.yaml')
                if not client.write_file(yaml.dumps(web_config), web_config_path):
                    stdio.error('{}: failed to write web config {}'.format(server, web_config_path))
                    return False
            except Exception as e:
                stdio.exception(e)
                return False
            cmd_items.append('--web.config.file={}'.format(web_config_path))

        additional_parameters = server_config.get('additional_parameters')
        if additional_parameters:
            for parameter in additional_parameters:
                if isinstance(parameter, dict):
                    for k, v in parameter.items():
                        if k in invalid_keys:
                            stdio.warn('{} invalid additional parameter {}.'.format(server, k))
                        cmd_items.append('--{}={}'.format(k, v))
                else:
                    if parameter in invalid_keys:
                        stdio.warn('{} invalid additional parameter {}'.format(server, parameter))
                    cmd_items.append('--{}'.format(parameter))
        cmd_args_map[server] = cmd_items
            
    plugin_context.set_variable('cmd_args_map', cmd_args_map)
    plugin_context.set_variable('use_parameter', use_parameter)
    return plugin_context.return_true()

