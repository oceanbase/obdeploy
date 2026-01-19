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

from _rpm import Version
from _stdio import FormatText
from tool import get_metadb_info_from_depends_ob, Cursor


def upgrade_pre(plugin_context, run_workflow, get_workflows, upgrade_ctx, upgrade_mode, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_original_global_conf()
    stdio = plugin_context.stdio

    upgrade_repositories = kwargs.get('upgrade_repositories')

    cur_repository = upgrade_repositories[0]
    dest_repository = upgrade_repositories[-1]
    repository_dir = dest_repository.repository_dir
    kwargs['repository_dir'] = repository_dir
    plugin_context.set_variable('cur_version', cur_repository.version)

    if cur_repository.version < Version('4.1.1'):
        stdio.print(FormatText.error('The current version of OMS is not supported for upgrade. Must be higher than 4.1.1 .'))
        return plugin_context.return_false()
    if not upgrade_mode:
        upgrade_map = {"1": "offline", "2": "online"}
        stdio.print(FormatText.warning('    Two types of OMS upgrade methods. Please choose one:'))
        stdio.print(f'    {1}) Offline upgrade: Start a new container with the new image to replace the container with the old version image. The running migration tasks will be interrupted during the upgrade process.')
        stdio.print(f'    {2}) Online upgrade: Replace the component packages in the original container with those from the new image. The running migration tasks will not be affected.')
        while True:
            number = stdio.read('Enter the number of the oceanbase type you want to use: ', blocked=True).strip()
            if not number or not number.isdigit() or int(number) not in [1, 2]:
                stdio.print(FormatText.error('Invalid number. Please try again.'))
                continue
            upgrade_mode = upgrade_map[str(number)]
            break

    if upgrade_mode == 'offline':
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
                    if k.find('enable') != -1 and v:
                        stdio.error('ha is enabled, please disable it before upgrade')
                        return plugin_context.return_false()

        offline_upgrade_workflow = get_workflows('offline_upgrade', repositories=[cur_repository])
        if not run_workflow(offline_upgrade_workflow, repositories=[cur_repository]):
            return plugin_context.return_false()
        start_kwargs = {'upgrade': True}
        offline_upgrade_start_workflow = get_workflows('offline_upgrade_start', repositories=[dest_repository])
        if not run_workflow(offline_upgrade_start_workflow, repositories=[dest_repository], **{dest_repository.name: start_kwargs}):
            return plugin_context.return_false()
    else:
        component_kwargs = kwargs.get('comp_kwargs') or {}
        online_upgrade_workflow = get_workflows('online_upgrade', repositories=[cur_repository])
        upgrade_kwargs = {'dest_repository': dest_repository}
        upgrade_kwargs.update(component_kwargs)
        if not run_workflow(online_upgrade_workflow, repositories=[cur_repository], **{cur_repository.name: upgrade_kwargs}):
            return plugin_context.return_false()
    upgrade_ctx["index"] += 1

    plugin_context.set_variable('finally_script_is_docker_init', False)
    return plugin_context.return_true()







