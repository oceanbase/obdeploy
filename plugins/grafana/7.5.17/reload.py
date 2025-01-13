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

from tool import YamlLoader

import re

yaml = YamlLoader()


def reload(plugin_context, new_cluster_config,  *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    servers = cluster_config.servers
    cursor = plugin_context.get_return('connect').get_return('cursor')

    stdio.start_loading('Reload Grafana')
    global_ret = True
    for server in servers:
        stdio.verbose('%s reload grafana ' % server)
        new_server_config = new_cluster_config.get_server_conf(server)
        api_cursor = cursor.get(server)
        grafana_new_pwd = new_server_config['login_password']
        if grafana_new_pwd == 'admin':
            stdio.error("%s grafana admin password should not be 'admin'" % server)
            global_ret = False
            continue
        if len(grafana_new_pwd) < 5:
            stdio.error("%s grafana admin password length should not be less than 5" % server)
            global_ret = False
            continue
        ret = api_cursor.modify_password(grafana_new_pwd, stdio=stdio)
        if ret:
            cluster_config.update_server_conf(server, 'login_password', grafana_new_pwd, False)
        else:  
            global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
