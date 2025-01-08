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
    return plugin_context.return_true()
