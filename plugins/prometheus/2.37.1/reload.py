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

import os

from tool import YamlLoader


def reload(plugin_context, cursor, new_cluster_config, deploy_name='<deploy name>',  *args, **kwargs):

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
