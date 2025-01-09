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
