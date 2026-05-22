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

check_port_keys = ['mgragent_http_port', 'monagent_http_port']


def obagent_const(plugin_context, **kwargs):
    cluster_config = plugin_context.cluster_config
    OBAGNET_CONFIG_MAP = {
        "sql_port": "{mysql_port}",
        "rpc_port": "{rpc_port}",
        "cluster_name": "{appname}",
        "cluster_id": "{cluster_id}",
        "zone_name": "{zone}",
        "ob_log_path": "{home_path}/store",
        "ob_data_path": "{home_path}/store",
        "ob_install_path": "{home_path}",
        "observer_log_path": "{home_path}/log",
    }
    depends_keys = []
    has_seekdb = const.COMP_OB_SEEKDB in cluster_config.depends
    if has_seekdb:
        OBAGNET_CONFIG_MAP["monitor_password"] = "{seekdb_monitor_password}"
        OBAGNET_CONFIG_MAP["monitor_user"] = "{seekdb_monitor_user}"
        OBAGNET_CONFIG_MAP.pop("cluster_name", None)
        OBAGNET_CONFIG_MAP.pop("zone_name", None)
        OBAGNET_CONFIG_MAP.pop("cluster_id", None)
        depends_keys = ["seekdb_monitor_password", "seekdb_monitor_user"]
        OBAGNET_CONFIG_MAP["ob_monitor_status"] = "inactive"
        OBAGNET_CONFIG_MAP["seekdb_monitor_status"] = "active"
    else:
        for comp in cluster_config.depends:
            if comp in const.COMPS_OB:
                OBAGNET_CONFIG_MAP["monitor_password"] = "{ocp_agent_monitor_password}"
                depends_keys = ["ocp_agent_monitor_password", "appname", "cluster_id"]
                break

    plugin_context.set_variable('OBAGNET_CONFIG_MAP', OBAGNET_CONFIG_MAP)
    plugin_context.set_variable('depends_keys', depends_keys)
    plugin_context.set_variable('check_port_keys', check_port_keys)
    return plugin_context.return_true()
