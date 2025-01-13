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

from _rpm import Version


def upgrade_check(plugin_context, upgrade_repositories, *args, **kwargs):
    stdio = plugin_context.stdio
    dest_repository = upgrade_repositories[1]
    if dest_repository.version >= Version('4.2.1'):
        for repository in plugin_context.repositories:
            if repository.name == 'obagent' and repository.version < Version('4.2.1'):
                stdio.error('OCP express {} requires obagent with version 4.2.1 or above, current obagent version is {}'.format(dest_repository.version, repository.version))
                return False

    plugin_context.return_true()
