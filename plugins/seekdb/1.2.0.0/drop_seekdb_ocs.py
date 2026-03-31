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

"""Start OBShell after SeekDB is up. Reference: OceanBase 4.2.1.4 obshell_start."""

from __future__ import absolute_import, division, print_function

def drop_seekdb_ocs(plugin_context, cursors={}, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.verbose('drop ocs')
    if plugin_context.get_variable('seekdb_is_standby', default=False):
        stdio.print('Standby cluster: skip drop ocs.')
        return plugin_context.return_true()
    standby_deploy_name = plugin_context.get_variable('standby_deploy_name')
    standby_cursor = cursors.get(standby_deploy_name)
    sql = "drop database ocs"
    standby_cursor.execute(sql, stdio=stdio)
    return plugin_context.return_true()
