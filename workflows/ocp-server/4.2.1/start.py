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


def start(plugin_context, workflow, *args, **kwargs):
    repositories = plugin_context.repositories
    clients = kwargs.get('component_kwargs', {}).get('new_clients', {})
    repository_name = [repository.name for repository in repositories]

    workflow.add(const.STAGE_FIRST, 'parameter_pre', 'ocp_const')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {'new_clients': clients}, 'chown_dir')
    if not plugin_context.cluster_config.depends:
        workflow.add_with_kwargs(const.STAGE_FIRST, {'need_connect': False}, 'cursor_check')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, const.COMP_OB_CE if const.COMP_OB_CE in repository_name else const.COMP_OB, '4.0.0.0', {'scale_out_component': const.COMP_OCP_SERVER_CE}, 'connect', 'create_tenant', 'create_user', 'import_time_zone')
    workflow.add(const.STAGE_FIRST, 'start', 'health_check')
    workflow.add(const.STAGE_FIRST, 'stop_pre')
    workflow.add_with_component(const.STAGE_FIRST, 'general', 'stop')
    workflow.add(const.STAGE_FIRST, 'start', 'health_check', 'bootstrap', 'connect', 'upload_packages')
    plugin_context.return_true()
