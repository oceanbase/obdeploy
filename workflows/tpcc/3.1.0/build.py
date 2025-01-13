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

def build(plugin_context, workflow, *args, **kwargs):
    repository = None
    for tmp_repository in plugin_context.repositories:
        if tmp_repository.name == getattr(plugin_context.options, 'component'):
            repository = tmp_repository
            break

    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'tpcc', repository.version, {"repository": repository}, 'build_pre')
    workflow.add_with_component_version_kwargs(const.STAGE_SECOND, 'tpcc', repository.version, {"repository": repository}, 'build')

    return plugin_context.return_true()
