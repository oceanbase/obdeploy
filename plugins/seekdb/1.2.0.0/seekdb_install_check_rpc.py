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

"""SeekDB install: connect to selected primary, check enable_rpc_service and log_disk_size; store via set_variable."""

from __future__ import absolute_import, division, print_function

from tool import Cursor


def seekdb_install_check_rpc(plugin_context, deploy_manager=None, *args, **kwargs):
    stdio = plugin_context.stdio
    mode = plugin_context.get_variable('install_mode', spacename='interactive')
    if mode != 'standby':
        return plugin_context.return_true()
    deploy_name = plugin_context.get_variable('selected_primary_deploy_name', spacename='interactive')
    plugin_context.set_variable('primary_deploy_name', deploy_name)
    if not deploy_name or not deploy_manager:
        stdio.error('selected_primary_deploy_name or deploy_manager missing.')
        return plugin_context.return_false()
    deploy = deploy_manager.get_deploy_config(deploy_name)
    if not deploy:
        stdio.error('Deploy "%s" not found.' % deploy_name)
        return plugin_context.return_false()
    cluster_config = deploy.deploy_config.components.get('seekdb')
    if not cluster_config or not cluster_config.servers:
        stdio.error('SeekDB config or servers not found for "%s".' % deploy_name)
        return plugin_context.return_false()
    server = cluster_config.servers[0]
    server_config = cluster_config.get_server_conf_with_default(server)
    primary_ip = server.ip
    primary_port = server_config.get('mysql_port', 2881)
    primary_password = server_config.get('root_password') or ''
    stdio.start_loading('Connect to primary (%s:%s)' % (primary_ip, primary_port))
    primary_rpc_info = {"primary_ip": primary_ip, "rpc_port": 2882}
    try:
        cursor = Cursor(ip=primary_ip, port=primary_port, tenant='', password=primary_password or '', stdio=stdio)
    except Exception as e:
        stdio.stop_loading('fail')
        stdio.error('Failed to connect to primary: %s' % e)
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    try:
        row = cursor.fetchone("SHOW parameters LIKE 'enable_rpc_service'")
        rpc_enabled = str(row['value']).lower() == 'true'
        cursor.execute('use oceanbase;')
        rpc_port = cursor.fetchone("select rpc_port from __all_virtual_server_stat;")['rpc_port']
        if rpc_port:
            primary_rpc_info["rpc_port"] = int(rpc_port)
    except Exception as e:
        stdio.error('Failed to fetch rpc port: %s' % e)
        rpc_enabled = False
    plugin_context.set_variable('primary_rpc_enabled', rpc_enabled)
    plugin_context.set_variable('primary_deploy_name', deploy_name)
    if not rpc_enabled:
        plugin_context.set_variable('need_rpc_choice', True)
    primary_log_disk_size = None
    try:
        primary_log_disk_size = cursor.fetchone("SHOW parameters LIKE 'log_disk_size'")['value']
    except Exception:
        pass
    plugin_context.set_variable('primary_log_disk_size', primary_log_disk_size)
    plugin_context.set_variable('primary_rpc_info', primary_rpc_info)
    cursor.close()
    return plugin_context.return_true()
