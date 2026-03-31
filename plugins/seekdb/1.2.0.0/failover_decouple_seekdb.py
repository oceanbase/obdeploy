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

def failover_decouple_seekdb(plugin_context, cursors={}, *args, **kwargs):
    stdio = plugin_context.stdio
    deploy_name = plugin_context.cluster_config.deploy_name
    
    stdio.start_loading('Failover SeekDB cluster')
    
    standby_cursor = cursors.get(deploy_name)
    if not standby_cursor:
        stdio.error('Failed to connect deploy: {}.'.format(deploy_name))
        return plugin_context.return_false()

    try:
        sql = "ALTER SYSTEM ACTIVATE STANDBY"
        standby_cursor.execute(sql, raise_exception=True, stdio=stdio)
        stdio.verbose("Executed: {}".format(sql))
    except Exception as e:
        stdio.error("Failed to activate standby cluster: {}".format(e))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    plugin_context.set_variable('start_obshell', True)
    return plugin_context.return_true()
