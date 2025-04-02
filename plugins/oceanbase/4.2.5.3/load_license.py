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

def load_license(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading('Wait for observer license register')
    license_file_path = plugin_context.get_variable("license_file_path")
    sql = "ALTER SYSTEM LOAD LICENSE '%s';" % license_file_path
    try:
        cursor.execute(sql, raise_exception=True)
    except Exception as e:
        stdio.error(e)
        stdio.stop_loading('failed')
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()