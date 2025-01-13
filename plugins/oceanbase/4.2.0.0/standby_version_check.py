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

def standby_version_check(plugin_context, repository, primary_repositories, *args, **kwargs):
    stdio = plugin_context.stdio
    if not primary_repositories:
        stdio.error('Primary repositories not found.')
        return False
    for primary_repository in primary_repositories:
        if repository.name == primary_repository.name:
            if repository.version == primary_repository.version:
                return plugin_context.return_true()
            else:
                stdio.error('Version not match. standby version: {} , primary version: {}.'.format(repository.version, primary_repository.version))
                return False

    return plugin_context.return_false()

