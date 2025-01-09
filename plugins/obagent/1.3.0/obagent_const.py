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


OBAGNET_CONFIG_MAP = {
        "monitor_password": "{ocp_agent_monitor_password}",
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

depends_keys = ["ocp_agent_monitor_password", "appname", "cluster_id"]

check_port_keys = ['mgragent_http_port', 'monagent_http_port']


def obagent_const(plugin_context, **kwargs):
    plugin_context.set_variable('OBAGNET_CONFIG_MAP', OBAGNET_CONFIG_MAP)
    plugin_context.set_variable('depends_keys', depends_keys)
    plugin_context.set_variable('check_port_keys', check_port_keys)
    return plugin_context.return_true()