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


def add_component_pre(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    if const.COMP_OB_CONFIGSERVER in added_components:
        cluster_config.add_depend_component(const.COMP_OB_CONFIGSERVER)
    if cluster_config.name not in added_components:
        return plugin_context.return_true()
    workflow.add_with_kwargs(const.STAGE_FIRST, {'auto_depend': True}, 'generate_config')
    repositories = plugin_context.repositories
    repository_names = [repository.name for repository in repositories]
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'oceanbase-ce' if 'oceanbase-ce' in repository_names else 'oceanbase',
                                               '4.0.0.0', {'scale_out_component': plugin_context.cluster_config.name}, 'connect')
    workflow.add(const.STAGE_FIRST, 'init', 'start_check_pre', 'status_check', 'password_check', 'status_check', 'work_dir_check', 'port_check')
    workflow.add(const.STAGE_THIRD, 'parameter_pre')
    plugin_context.return_true()
