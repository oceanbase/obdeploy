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


def add_component(plugin_context, workflow, *args, **kwargs):
    workflow.add(const.STAGE_FIRST, 'start_check', 'start', 'health_check')
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    exist_obproxy = True
    repositories = plugin_context.repositories
    repository_names = [repository.name for repository in repositories]
    workflow.add_with_component(const.STAGE_FIRST, const.COMP_OB_CE if const.COMP_OB_CE in repository_names else const.COMP_OB, 'connect', 'configserver_pre', 'register_configserver')
    has_obproxy = False
    for comp in const.COMPS_ODP:
        if comp in added_components:
            exist_obproxy = False
        if comp in repository_names:
            has_obproxy = True
    if exist_obproxy and has_obproxy:
        workflow.add_with_component(const.STAGE_FIRST, const.COMP_ODP_CE if const.COMP_ODP_CE in repository_names else const.COMP_ODP,  'connect', 'parameter_pre', 'register_configserver')

    workflow.add(const.STAGE_THIRD, 'connect', 'display')
    plugin_context.return_true()
