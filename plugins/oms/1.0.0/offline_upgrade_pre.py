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

from tool import Cursor, get_metadb_info_from_depends_ob


def offline_upgrade_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global_config = cluster_config.get_original_global_conf()

    ob_metadb_info = get_metadb_info_from_depends_ob(cluster_config, stdio)
    if ob_metadb_info:
        oms_meta_host = ob_metadb_info['host']
        oms_meta_port = ob_metadb_info['port']
        oms_meta_user = ob_metadb_info['user']
        oms_meta_password = ob_metadb_info['password']
    else:
        oms_meta_host = global_config.get('oms_meta_host')
        oms_meta_port = global_config.get('oms_meta_port')
        oms_meta_user = global_config.get('oms_meta_user')
        oms_meta_password = global_config.get('oms_meta_password')

    try:
        cursor = Cursor(ip=oms_meta_host, user=oms_meta_user, port=int(oms_meta_port), tenant='', password=oms_meta_password, stdio=stdio)
    except:
        stdio.error('Connect OMS cm meta fail')
        return plugin_context.return_false()
    regions = global_config.get('regions', [])
    drc_cm_heartbeat_dbs = set()
    for region in regions:
        drc_cm_heartbeat_db = region.get('drc_cm_heartbeat_db') or (global_config.get('drc_cm_heartbeat_db', 'oms_cm_heartbeat') + "_" + str(region['cm_location']))
        drc_cm_heartbeat_dbs.add(drc_cm_heartbeat_db)

    for drc_cm_heartbeat_db in drc_cm_heartbeat_dbs:
        cursor.execute('use %s' % drc_cm_heartbeat_db)
        cursor.execute('delete from heatbeat_sequence where id < (select max(id) from heatbeat_sequence);')
    plugin_context.set_variable('cursor', cursor)

    return plugin_context.return_true()







