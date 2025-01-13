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

global_ret = True

def destroy_pre(plugin_context, *args, **kwargs):
    def clean_database(cursor, database):
        ret = cursor.execute("drop database {0}".format(database))
        if not ret:
            global global_ret
            global_ret = False
        cursor.execute("create database if not exists {0}".format(database))
    
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global global_ret

    plugin_context.set_variable("clean_dirs", ['log_dir'])
    if plugin_context.get_variable('clean_data'):
        stdio.start_loading('ocp-express metadb cleaning')
        stdio.verbose("clean metadb")
        meta_cursor = plugin_context.get_variable('cursor')
        database = plugin_context.get_variable('database')
        try:
            clean_database(meta_cursor, database)
        except Exception:
            stdio.error("failed to clean meta data")
            global_ret = False
    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
