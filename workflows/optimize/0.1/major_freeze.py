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

def major_freeze(plugin_context, workflow, repository, *args, **kwargs):
    connect_namespaces = kwargs.get("connect_namespaces")
    ob_repository = kwargs.get("ob_repository")
    restart_components = kwargs.get("restart_components")
    optimize_envs = kwargs.get("optimize_envs")

    stdio = plugin_context.stdio
    if not connect_namespaces:
        pass
    for namespace in connect_namespaces:
        workflow.add_with_component_version_kwargs(const.STAGE_FIRST, repository.name, repository.version, {"spacename": namespace.spacename}, 'connect')
        if namespace.spacename == ob_repository.name and ob_repository.name in restart_components:
            stdio.verbose('{}: major freeze for component ready'.format(ob_repository.name))
            workflow.add_with_component_version_kwargs(const.STAGE_SECOND, ob_repository.name, ob_repository.version, {"tenant": optimize_envs.get('tenant')}, 'major_freeze')
    return plugin_context.return_true()
            
    

