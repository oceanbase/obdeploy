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


def reinstall(plugin_context, workflow, *args, **kwargs):
    component_name = plugin_context.cluster_config.name

    workflow.add_with_kwargs(const.STAGE_FIRST, {'is_reinstall': True}, 'configserver_pre', 'start_pre', 'start', 'health_check')
    if const.COMP_OB_CE == component_name:
        workflow.add_with_kwargs(const.STAGE_FIRST, {'is_reinstall': True}, 'obshell_start')
    plugin_context.return_true()

