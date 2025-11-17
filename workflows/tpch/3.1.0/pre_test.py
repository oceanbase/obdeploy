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

def pre_test(plugin_context, workflow, repository, *args, **kwargs):
    target_repository_version = '4.3.0.0' if repository.name == const.COMP_OB_SEEKDB else repository.version
    workflow.add_with_component_version(const.STAGE_FIRST, repository.name, repository.version, 'connect')
    workflow.add_with_component_version_kwargs(const.STAGE_SECOND, 'tpch', target_repository_version, {"repository": repository}, 'parameter_pre')
    workflow.add_with_component_version_kwargs(const.STAGE_SECOND, 'tpch', target_repository_version,{"repository": repository}, 'pre_test')
    return plugin_context.return_true()
