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


def reload(plugin_context, new_cluster_config, deploy_name='<deploy name>',  *args, **kwargs):

    def generate_or_update_config(config):
        if client.execute_command('ls {}'.format(runtime_prometheus_conf)):
            try:
                ret = client.execute_command('cat {}'.format(runtime_prometheus_conf))
                if not ret:
                    stdio.error(ret.stderr)
                    return False
                prometheus_conf_content = yaml.loads(ret.stdout.strip())
            except:
                stdio.exception('{} invalid prometheus config {}'.format(server, runtime_prometheus_conf))
                stdio.stop_loading('fail')
                return False
        else:
            prometheus_conf_content = {'global': None}
        if config:
            prometheus_conf_content.update(config)
        try:
            config_content = yaml.dumps(prometheus_conf_content).strip()
            if not client.write_file(config_content, runtime_prometheus_conf):
                stdio.error('{} failed to write config file {}'.format(server, runtime_prometheus_conf))
                return False
            return True
        except Exception as e:
            stdio.exception("{} failed to update config. {}".format(server, e))
            return False

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    cursor = plugin_context.get_return('connect').get_return('cursor')
    yaml = YamlLoader(stdio=stdio)
    stdio.start_loading('Reload prometheus')
    success = True
    for server in servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        api_cursor = cursor.get(server)
        enable_lifecycle = server_config['enable_lifecycle']
        home_path = server_config['home_path']
        if enable_lifecycle:
            runtime_prometheus_conf = os.path.join(home_path, 'prometheus.yaml')
            new_config = new_cluster_config.get_server_conf(server).get('config')
            if not generate_or_update_config(new_config):
                success = False
                continue
            if not api_cursor.reload(stdio=stdio):
                success = False
        else:
            stdio.error('{} do not enable lifecycle, please use `obd cluster restart {} --wp` '
                       'If you still want the changes to take effect'.format(server, deploy_name))
            success = False
    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
