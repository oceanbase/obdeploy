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

import const


def obagent_const(plugin_context, **kwargs):
    oceanbase_config_map = {
        "monitor_password": "{ocp_agent_monitor_password}",
        "monitor_user": "{ocp_agent_monitor_username}",
        "cluster_name": "{appname}",
        "zone_name": "{zone}",
        "cluster_id": "{cluster_id}",
    }

    seekdb_config_map = {
        "monitor_password": "{seekdb_monitor_password}",
        "monitor_user": "{seekdb_monitor_user}",
        "ob_monitor_status": "inactive",
        "seekdb_monitor_status": "active",
    }

    OBAGNET_CONFIG_MAP = {
        "sql_port": "{mysql_port}",
        "rpc_port": "{rpc_port}",
        "ob_log_path": "{home_path}/store",
        "ob_data_path": "{home_path}/store",
        "ob_install_path": "{home_path}",
        "observer_log_path": "{home_path}/log",
    }

    depends_keys = []

    oceanbase_depends_keys = ["ocp_agent_monitor_username", "ocp_agent_monitor_password", "appname", "cluster_id"]
    seekdb_depends_keys = ["seekdb_monitor_password", "seekdb_monitor_user"]

    check_port_keys = ['mgragent_http_port', 'monagent_http_port']
    cluster_config = plugin_context.cluster_config
    depends = const.COMPS_OB
    for comp in cluster_config.depends:
        if comp in depends:
            OBAGNET_CONFIG_MAP.update(oceanbase_config_map)
            depends_keys = oceanbase_depends_keys
            break
        if comp == const.COMP_OB_SEEKDB:
            OBAGNET_CONFIG_MAP.update(seekdb_config_map)
            depends_keys = seekdb_depends_keys
            break

    plugin_context.set_variable('OBAGNET_CONFIG_MAP', OBAGNET_CONFIG_MAP)
    plugin_context.set_variable('depends_keys', depends_keys)
    plugin_context.set_variable('check_port_keys', check_port_keys)
    return plugin_context.return_true()