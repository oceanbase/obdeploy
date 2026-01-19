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

import os

import const
from ssh import LocalClient


def start(plugin_context, workflow, *args, **kwargs):
    repositories = plugin_context.repositories
    workflow.add(const.STAGE_FIRST, 'parameter_pre')
    repository_name = [repository.name for repository in repositories]

    cluster_config = plugin_context.cluster_config
    server = cluster_config.servers[0]
    server_config = cluster_config.get_server_conf(server)

    bootstrap_path = os.path.join(server_config['home_path'], '.bootstrap')
    cmd = 'ls %s' % bootstrap_path
    if not LocalClient.execute_command(cmd):
        for ob in const.COMPS_OB:
            if ob in repository_name:
                workflow.add_with_component_version_kwargs(const.STAGE_FIRST, ob, '4.0.0.0', {'scale_out_component': const.COMP_PRAG}, 'connect', 'create_tenant', 'create_user')
                workflow.add(const.STAGE_FIRST, 'init_db')
    workflow.add(const.STAGE_FIRST, 'generate_env_file', 'get_services_status', 'start')
    return plugin_context.return_true()
