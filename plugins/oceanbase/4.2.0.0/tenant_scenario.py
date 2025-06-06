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
import json
import os

from tool import FileUtil


def tenant_scenario(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    repositories = plugin_context.repositories

    scenarios = set()
    path = ''
    for repository in repositories:
        if repository.name == cluster_config.name:
            path = repository.repository_dir
            break

    system_variable_json = f'{path}/etc/default_system_variable.json'
    default_parameters_json = f'{path}/etc/default_parameter.json'
    for file in [system_variable_json, default_parameters_json]:
        if os.path.exists(file):
            with FileUtil.open(file, 'rb') as f:
                data = json.load(f)
                for _ in data:
                    scenarios.add(_['scenario'])

    return plugin_context.return_true(scenarios=scenarios)
