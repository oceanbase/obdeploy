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


OBAGNET_CONFIG_MAP = {
    "monitor_password": "{ocp_agent_monitor_password}",
    "monitor_user": "{ocp_agent_monitor_username}",
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

depends_keys = ["ocp_agent_monitor_username", "ocp_agent_monitor_password", "appname", "cluster_id"]

check_port_keys = ['mgragent_http_port', 'monagent_http_port']


def obagent_const(plugin_context, **kwargs):
    plugin_context.set_variable('OBAGNET_CONFIG_MAP', OBAGNET_CONFIG_MAP)
    plugin_context.set_variable('depends_keys', depends_keys)
    plugin_context.set_variable('check_port_keys', check_port_keys)
    return plugin_context.return_true()