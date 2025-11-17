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
import _errno as err
from tool import Cursor


def connect_db_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    check_pass = plugin_context.get_variable('check_pass')
    error = plugin_context.get_variable('error')
    wait_2_pass = plugin_context.get_variable('wait_2_pass')
    stdio.start_loading('check connect db')
    if plugin_context.get_variable('connect_check_pass'):
        for server in cluster_config.servers:
            check_pass(server, 'connect_db')
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    global_config = cluster_config.get_original_global_conf()
    oms_meta_host = global_config.get('oms_meta_host')
    oms_meta_port = global_config.get('oms_meta_port')
    oms_meta_user = global_config.get('oms_meta_user')
    oms_meta_password = global_config.get('oms_meta_password')

    if oms_meta_password == "":
        for server in cluster_config.servers:
            check_pass(server, 'connect_db')
        stdio.stop_loading('fail')
        stdio.error('OMS meta password is not support empty')
        return plugin_context.return_false()

    if global_config.get('tsdb_service') == 'INFLUXDB':
        from influxdb import InfluxDBClient
        url = global_config.get('tsdb_url')
        host = url.split(':')[0]
        port = url.split(':')[1]
        client = InfluxDBClient(host=host, port=int(port), username=global_config.get('tsdb_username'), password=global_config.get('tsdb_password'))
        if not client.ping():
            for server in cluster_config.servers:
                error(server, 'connect_db', err.EC_OMS_SERVER_CONNECT_INFLUXDB, [err.SUG_CHECK_CONNECT_INFO.format(db='influxdb')])

    for ob_comp in const.COMPS_OB:
        if ob_comp in cluster_config.depends:
            for server in cluster_config.servers:
                check_pass(server, 'connect_db')
            break
    else:
        try:
            Cursor(ip=oms_meta_host, user=oms_meta_user, port=int(oms_meta_port), tenant='', password=oms_meta_password, stdio=stdio)
        except:
            for server in cluster_config.servers:
                error(server, 'connect_db', err.EC_OCP_SERVER_CONNECT_METADB, [err.SUG_CHECK_CONNECT_INFO.format(db='metadb')])

    for server in cluster_config.servers:
        wait_2_pass(server)

    success = plugin_context.get_variable('get_success')()
    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
