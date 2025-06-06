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

def install_ob_utils(plugin_context, install_utils_to_servers, get_repositories_utils, *args, **kwargs):
    repositories = plugin_context.repositories
    repositories_utils_map = get_repositories_utils(repositories)
    ret = install_utils_to_servers(repositories, repositories_utils_map)
    if not ret:
        return plugin_context.return_false()
    return plugin_context.return_true()