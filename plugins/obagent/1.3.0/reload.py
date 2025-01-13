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
import json
from copy import deepcopy
from glob import glob
from tool import YamlLoader, FileUtil

from _errno import *


def reload(plugin_context, new_cluster_config, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    cursor = plugin_context.get_return('connect').get_return('cursor')
    servers = cluster_config.servers

    for repository in plugin_context.repositories:
        if repository.name == cluster_config.name:
            break
    repository_dir = repository.repository_dir

    yaml = YamlLoader(stdio)
    config_map = {
        "monitor_password": "root_password",
        "sql_port": "mysql_port",
        "rpc_port": "rpc_port",
        "cluster_name": "appname",
        "cluster_id": "cluster_id",
        "zone_name": "zone",
    }
    global_change_conf = {}
    for comp in ['oceanbase', 'oceanbase-ce']:
        if comp in cluster_config.depends:
            root_servers = {}
            ob_config = cluster_config.get_depend_config(comp)
            new_ob_config = new_cluster_config.get_depend_config(comp)
            ob_config = {} if ob_config is None else ob_config
            new_ob_config = {} if new_ob_config is None else new_ob_config
            for key in config_map:
                if ob_config.get(key) != new_ob_config.get(key):
                    global_change_conf[config_map[key]] = new_ob_config.get(key)

    global_ret = True
    stdio.start_loading('Reload obagent')
    for server in servers:
        change_conf = deepcopy(global_change_conf)
        client = clients[server]
        api_cursor = cursor.get(server)
        stdio.verbose('get %s old configuration' % (server))
        config = cluster_config.get_server_conf_with_default(server)
        stdio.verbose('get %s new configuration' % (server))
        new_config = new_cluster_config.get_server_conf_with_default(server)
        stdio.verbose('get %s cluster address' % (server))
        stdio.verbose('compare configuration of %s' % (server))
        with FileUtil.open(os.path.join(repository_dir, 'conf/obd_agent_mapper.yaml')) as f:
            data = yaml.load(f).get('config_mapper', {})
            for key in new_config:
                if key not in data:
                    stdio.warn('%s no in obd_agent_mapper.yaml, skip' % key)
                    continue
                if key not in config or config[key] != new_config[key]:
                    item = cluster_config.get_temp_conf_item(key)
                    if item:
                        if item.need_redeploy or item.need_restart:
                            stdio.verbose('%s can not be reload' % key)
                            global_ret = False
                            continue
                        try:
                            item.modify_limit(config.get(key), new_config.get(key))
                        except Exception as e:
                            stdio.verbose('%s: %s' % (server, str(e)))
                            global_ret = False
                            continue
                    change_conf[key] = new_config[key]
        
        if change_conf:
            stdio.verbose('%s apply new configuration' % server)
            data = [{'key': key, 'value': change_conf[key]} for key in change_conf]
            if not (api_cursor and api_cursor.reload(data, stdio)):
                global_ret = False
                stdio.error(EC_OBAGENT_RELOAD_FAILED.format(server=server))
    
    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return
