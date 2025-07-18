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


def add_component_pre(plugin_context, workflow, ob_repository, *args, **kwargs):
    workflow.add(const.STAGE_FIRST, 'scale_out_check', 'parameter_pre')
    workflow.add_with_kwargs(const.STAGE_FIRST, {'auto_depend': True}, 'generate_config')
    workflow.add_with_component_version_kwargs(const.STAGE_SECOND, ob_repository.name, '4.0.0.0', {'scale_out_component': const.COMP_OCP_SERVER_CE if const.COMP_OCP_SERVER_CE in repository_names else const.COMP_OCP_SERVER}, 'connect', 'create_tenant', 'create_user', 'import_time_zone')

    workflow.add(const.STAGE_THIRD, 'init')
    plugin_context.return_true()
