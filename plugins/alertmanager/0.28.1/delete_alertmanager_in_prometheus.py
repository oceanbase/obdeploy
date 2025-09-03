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

def delete_alertmanager_in_prometheus(plugin_context, *args, **kwargs):
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    yaml = YamlLoader(stdio)
    global_ret = True

    if 'prometheus' in cluster_config.depends:
        prometheus_servers = cluster_config.get_depend_servers('prometheus')
        prometheus_cursors = plugin_context.get_return('connect', spacename='prometheus').get_return('cursors')
        for prometheus_server in prometheus_servers:
            client = clients[prometheus_server]
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
                raise e

            if 'alerting' in content and 'alertmanagers' in content['alerting']:
                for alertmanager in content['alerting']['alertmanagers']:
                    for static_config in alertmanager.get('static_configs', []):
                        targets = static_config.get('targets', [])
                        for server in cluster_config.servers:
                            server_config = cluster_config.get_server_conf(server)
                            ip = server.ip
                            port = server_config['port']
                            target = "%s:%s" % (ip, port)
                            if target in targets:
                                targets.remove(target)
                
                alertmanagers_to_remove = []
                for i, alertmanager in enumerate(content['alerting']['alertmanagers']):
                    static_configs_to_remove = []
                    for j, static_config in enumerate(alertmanager.get('static_configs', [])):
                        targets = static_config.get('targets', [])
                        if not targets:
                            static_configs_to_remove.append(j)
                    
                    for j in reversed(static_configs_to_remove):
                        del alertmanager['static_configs'][j]
                        if 'basic_auth' in alertmanager:
                            del alertmanager['basic_auth']
                    
                    if not alertmanager.get('static_configs'):
                        alertmanagers_to_remove.append(i)
                
                for i in reversed(alertmanagers_to_remove):
                    del content['alerting']['alertmanagers'][i]
                
                if not content['alerting'].get('alertmanagers') and len(content['alerting']) == 1:
                    del content['alerting']

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