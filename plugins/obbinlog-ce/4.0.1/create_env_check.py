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

import re

import const
import _errno
from _types import Capacity
from tool import ConfigUtil, Cursor, get_disk_info
from _errno import EC_OBBINLOG_TARGET_DEPLOY_NEED_CONFIGSERVER


def create_env_check(plugin_context, ob_deploy, ob_cluster_repositories, *args, **kwargs):

    cursor = plugin_context.get_return('target_ob_connect_check').get_return('ob_cursor')
    if not cursor:
        return plugin_context.return_false()

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    # resource check
    min_memory = 4 << 30
    min_disk = 10 << 30
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        # memory
        ret = client.execute_command('cat /proc/meminfo')
        if ret:
            for k, v in re.findall('(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
                if k == 'MemFree':
                    if Capacity(str(v)).bytes >= min_memory:
                        break
                    else:
                        stdio.warn(_errno.EC_OBSERVER_NOT_ENOUGH_MEMORY.format(ip=server.ip, free=str(Capacity(str(v)).bytes), need=str(min_memory)))
        # disk
        home_path = server_config['home_path']
        disk = get_disk_info(all_paths=home_path, client=client, stdio=stdio)
        stdio.verbose('disk: {}'.format(disk))
        kp = '/'
        for p in disk:
            if p in home_path:
                if len(p) > len(kp):
                    kp = p
        if disk[kp]['avail'] < min_disk:
            stdio.warn(_errno.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=server.ip, disk=kp, avail=str(disk[kp]['avail']), need=str(min_disk)))

    ob_repository = None
    for repository in ob_cluster_repositories:
        if repository.name in const.COMPS_OB:
            ob_repository = repository
            break
    ob_cluster_config = ob_deploy.deploy_config.components[ob_repository.name]
    ob_global_config = ob_cluster_config.get_global_conf()
    sql = "select * from oceanbase.DBA_OB_USERS where USER_NAME = 'cdcro';"
    if not cursor.fetchone(sql):
        pw = ConfigUtil.get_random_pwd_by_total_length()
        sql = 'create user if not exists "cdcro" IDENTIFIED BY %s'
        raise_cursor = cursor.raise_cursor
        raise_cursor.execute(sql, [pw])
        sql = 'grant select on oceanbase.* to cdcro IDENTIFIED BY %s'
        raise_cursor.execute(sql, [pw])
        ob_cluster_config.update_global_conf('cdcro_password', pw, True)
    else:
        if not ob_global_config.get('cdcro_password') and getattr(plugin_context.options, 'cdcro_password', None) is None:
            stdio.error('Connection observer failed, please check `cdcro_password`.')
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        if not ob_global_config.get('cdcro_password'):
            for server in ob_cluster_config.servers:
                ob_server_config = ob_cluster_config.get_server_conf(server)
                try:
                    Cursor(ip=server.ip, port=ob_server_config['mysql_port'], user='cdcro', tenant='', password=getattr(plugin_context.options, 'cdcro_password', None), stdio=stdio)
                    break
                except:
                    continue
            else:
                stdio.error('connect observer by cdcro failed. Please check `cdcro_password`.')
                return plugin_context.return_false()
            ob_cluster_config.update_global_conf('cdcro_password', getattr(plugin_context.options, 'cdcro_password'), True)
    try:
        ret = cursor.fetchone("SHOW PARAMETERS LIKE 'obconfig_url';")
        obconfig_url = ret['value']
        if not obconfig_url:
            stdio.error(EC_OBBINLOG_TARGET_DEPLOY_NEED_CONFIGSERVER.format(target_oceanbase_deploy=ob_deploy.name))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        plugin_context.set_variable('obconfig_url', obconfig_url)
    except Exception as e:
        stdio.error(e)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()

