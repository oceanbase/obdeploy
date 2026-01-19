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
from tool import get_option


def create_tenant(plugin_context, workflow, *args, **kwargs):
    workflow.add(const.STAGE_FIRST, 'create_tenant_pre', 'scenario_check', 'connect', 'create_tenant', 'create_user', 'import_time_zone', 'tenant_optimize')
    repository = kwargs.get('repository')
    if repository.name == const.COMP_OB_CE:
        workflow.add_with_kwargs(const.STAGE_FIRST, {"system_parameters": {'global_index_auto_split_policy': 'ALL'}}, 'alter_tenant_system_parameters')
    component_kwargs = kwargs.get("component_kwargs")
    create_tenant_options = None
    if component_kwargs and component_kwargs.get('create_tenant_options'):
        create_tenant_options = component_kwargs.get('create_tenant_options')[0]
    options = create_tenant_options if create_tenant_options else plugin_context.options
    if getattr(options, 'variables', None):
        workflow.add(const.STAGE_FIRST, 'set_tenant_whitelist')
    plugin_context.return_true()