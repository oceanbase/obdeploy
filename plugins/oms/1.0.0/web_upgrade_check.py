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

import json

import _errno as err
from _types import Capacity
from tool import get_metadb_info_from_depends_ob, Cursor


def web_upgrade_check(plugin_context, path=None, init_check_status=False, *args, **kwargs):
    def check_pass(item):
        status = check_status[server]
        if status[item].status == err.CheckStatus.WAIT:
            status[item].status = err.CheckStatus.PASS
    def check_fail(item, error, suggests=[]):
        status = check_status[server][item]
        status.error = error
        status.suggests = suggests
        status.status = err.CheckStatus.FAIL

    def error(item, _error, suggests=[]):
        success = False
        check_fail(item, _error, suggests)
        stdio.error(_error)


    check_status = {}
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_original_global_conf()
    plugin_context.set_variable('start_check_status', check_status)


    for server in cluster_config.servers:
        if path:
            check_status[server] = {
                'path': err.CheckStatus(),
            }
        else:
            check_status[server] = {
                'ha': err.CheckStatus(),
            }

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.start_loading('Check before upgrade %s' % cluster_config.name)
    success = True

    if path:
        for server in cluster_config.servers:
            client = clients[server]
            exist_ret = client.execute_command(f"if [ -e '{path}' ]; then echo exist; else echo not_exist; fi").stdout.strip()
            if exist_ret == 'exist':
                error('path', err.EC_FAIL_TO_INIT_PATH.format(server=server, key='', msg=err.InitDirFailedErrorMessage.NOT_EMPTY.format(path=path)))
                continue
            ret = client.execute_command(f"mkdir -p {path}")
            if not ret:
                error('path', err.EC_FAIL_TO_INIT_PATH.format(server=server, key='', msg=ret.stderr))
                continue
            if Capacity(client.execute_command(f"df -BG {path} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes < 20 << 30:
                error('path', err.EC_OMS_NOT_ENOUGH_DISK.format(ip=server.ip, disk=path, need='20G'))
            else:
                check_pass('path')
            client.execute_command(f"rm -rf {path}")
    else:
        if len(cluster_config.servers) > 1:
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
            drc_rm_db = global_config.get('drc_rm_db', 'oms_rm')
            cursor.execute('use %s' % drc_rm_db)
            rv = cursor.fetchone("select cfg_value from oms_normal_config where cfg_name='ha.config';")
            if rv:
                cfg_value = rv['cfg_value']
                if isinstance(cfg_value, str):
                    cfg_value = json.loads(cfg_value)
                for k, v in cfg_value.items():
                    if k.find('enable') != -1 and v is True:
                        for server in cluster_config.servers:
                            error('ha', err.EC_OMS_UPDATE_NOT_DISABLE_HA)
                        break
                else:
                    for server in cluster_config.servers:
                        check_pass('ha')
        else:
            check_pass('ha')


    plugin_context.set_variable('start_check_status', check_status)

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()



