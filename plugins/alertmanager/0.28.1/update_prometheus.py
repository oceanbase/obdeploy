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

from tool import YamlLoader

def update_prometheus(plugin_context, new_cluster_config=None, *args, **kwargs):
    clients = plugin_context.clients
    cluster_config = new_cluster_config if new_cluster_config else plugin_context.cluster_config
    stdio = plugin_context.stdio
    yaml = YamlLoader(stdio)
    global_ret = True
    use_parameter = plugin_context.get_variable('use_parameter')

    if 'prometheus' in cluster_config.depends and use_parameter:
        prometheus_cursors = plugin_context.get_return('connect', spacename='prometheus').get_return('cursor')
        prometheus_servers = cluster_config.get_depend_servers('prometheus')
        
        for prometheus_server in prometheus_servers:
            client = clients[prometheus_server]
            targets = []
            prometheus_server_config = cluster_config.get_depend_config('prometheus', prometheus_server)
            prometheus_home_path = prometheus_server_config['home_path']
            prometheus_conf_path = os.path.join(prometheus_home_path, 'prometheus.yaml')

            try:
                ret = client.execute_command('cat {}'.format(prometheus_conf_path))
                if not ret:
                    stdio.error(ret.stderr)
                    return False
                content = yaml.loads(ret.stdout.strip())
            except Exception as e:
                stdio.exception('failed to load prometheus config')
                return False
            
            if 'alerting' in content and 'alertmanagers' in content['alerting']:
                del content['alerting']['alertmanagers']

            content['alerting'] = {
                'alertmanagers': [
                    {
                        'static_configs': [
                            {
                                'targets': targets
                            }
                        ]
                    }
                ]
            }

            for server in cluster_config.servers:
                server_config = cluster_config.get_server_conf(server)
                ip = server.ip
                port = server_config['port']
                target = "%s:%s" % (ip, port)
                targets.append(target)

            if server_config.get('basic_auth_users'):
                username, password = list(server_config['basic_auth_users'].items())[0]
                content['alerting']['alertmanagers'][0]['basic_auth'] = {
                    'username': username,
                    'password': password
                }
                
            config_content = yaml.dumps(content).strip()
            if not client.write_file(config_content, prometheus_conf_path):
                stdio.error('failed to write config file {}'.format(prometheus_conf_path))
                return False
            
            stdio.start_loading('Reload prometheus %s' % prometheus_server.ip)
            if prometheus_cursors:
                prometheus_cursor = prometheus_cursors.get(prometheus_server)
                if not prometheus_cursor.reload(stdio=stdio):
                    global_ret = False
                    stdio.stop_loading('fail')  
            stdio.stop_loading('succeed')
    if global_ret:        
        return plugin_context.return_true()
    return plugin_context.return_false()