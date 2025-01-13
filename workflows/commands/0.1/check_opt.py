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

def check_opt(plugin_context, workflow, *args, **kwargs):
    kwargs = {
        "name": plugin_context.cmds[1],
        "context": {},
        "repository": plugin_context.repositories[0]
    }
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', plugin_context.repositories[0].version, {"repository": plugin_context.repositories[0]}, 'sync_cluster_config')
    workflow.add_with_component_version_kwargs(const.STAGE_SECOND, "commands", '0.1', kwargs, 'check_opt')
    plugin_context.return_true()