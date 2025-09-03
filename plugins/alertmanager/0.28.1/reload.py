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

import os

from tool import YamlLoader

def reload(plugin_context, new_cluster_config,  *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    cluster_receivers_conf = new_cluster_config.get_receivers_conf()
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    cursor = plugin_context.get_return('connect').get_return('cursor')
    yaml = YamlLoader(stdio=stdio)

    stdio.start_loading('Reload alertmanager')
    success = True
    for server in servers:
        client = clients[server]
        new_server_config = new_cluster_config.get_server_conf(server)
        api_cursor = cursor.get(server)
        home_path = new_server_config['home_path']
        runtime_alertmanager_conf = os.path.join(home_path, 'alertmanager.yaml')
        if 'receivers' in new_server_config and 'altermanager_config' in new_server_config:
            stdio.error("'receivers' and 'altermanager_config' conflict, please delete one")
            success = False
        
        if 'altermanager_config' in new_server_config:
            alertmanager_config = new_server_config.get('altermanager_config')
            config_tenant = yaml.dumps(alertmanager_config).strip()
            if not client.write_file(config_tenant, runtime_alertmanager_conf):
                stdio.error('{} failed to write config file {}'.format(server, alertmanager_config))
                success = False
        else:
            receivers = new_server_config['receivers']
            receiver_list = []

            for index, receiver in enumerate(receivers):
                if cluster_receivers_conf.get(receiver):
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
                altermanager_config = {
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
                
                altermanager_config = {
                    'route': {
                        'receiver': receivers[0],
                        'routes': routes
                    },
                    'receivers': receiver_list
                }

            config_tenant = yaml.dumps(altermanager_config)
            if not client.write_file(config_tenant, runtime_alertmanager_conf):
                stdio.error('failed to write config file {}'.format(runtime_alertmanager_conf))
                return False
        if not api_cursor.reload(stdio=stdio):
            success = False
    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
        