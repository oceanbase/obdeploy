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

from copy import copy


def upgrade(plugin_context, search_py_script_plugin, apply_param_plugin, run_workflow, get_workflows, *args, **kwargs):
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    upgrade_repositories = kwargs.get('upgrade_repositories')

    cur_repository = upgrade_repositories[0]
    dest_repository = upgrade_repositories[-1]
    repository_dir = dest_repository.repository_dir
    kwargs['repository_dir'] = repository_dir

    start_workflows = get_workflows("upgrade_start", repositories=[dest_repository])
    init_workflows = get_workflows("init", repositories=[dest_repository])
    stop_workflows = get_workflows("stop", repositories=[cur_repository])

    apply_param_plugin(cur_repository)
    if not run_workflow(stop_workflows, repositories=[cur_repository], **kwargs):
        return plugin_context.return_false()

    try:
        servers = cluster_config.servers
        for server in servers:
            client = clients[server]
            res = client.execute_command("sudo docker ps | grep ocp-all-in-one | awk '{print $1}'").stdout.strip()
            if res:
                client.execute_command("sudo docker ps | grep ocp-all-in-one | awk '{print $1}' | xargs sudo docker stop")
    except:
        pass

    apply_param_plugin(dest_repository)
    init_kwargs = copy(kwargs)
    init_kwargs['upgrade'] = True
    if not run_workflow(init_workflows, repositories=[dest_repository], **{dest_repository.name: init_kwargs}):
        return plugin_context.return_false()

    start_kwargs = copy(kwargs)
    start_kwargs['without_parameter'] = True
    if not run_workflow(start_workflows, repositories=[dest_repository], **{dest_repository.name: start_kwargs}):
        return plugin_context.return_false()
    upgrade_ctx = kwargs.get('upgrade_ctx')
    upgrade_ctx['index'] += 1
    return plugin_context.return_true()
