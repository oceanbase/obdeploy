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

def optimize(plugin_context, workflow, repository, *args, **kwargs):
    optimize_config = kwargs.get('optimize_config')
    connect_namespace = kwargs.get('connect_namespaces')
    get_db_and_cursor = kwargs.get("get_db_and_cursor")

    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'optimize', "0.1", {'optimize_config': optimize_config, 'repository': repository}, 'check_options')

    for namespace in connect_namespace:
        db, cursor = get_db_and_cursor(namespace)
        if not db or not cursor:
            workflow.add_with_component_version_kwargs(const.STAGE_SECOND, repository.name, repository.version, {"spacename": namespace.spacename}, 'connect')

    workflow.add_with_component_version_kwargs(const.STAGE_THIRD, 'optimize', "0.1", {'repository': repository, **kwargs}, 'optimize')

    return plugin_context.return_true()

