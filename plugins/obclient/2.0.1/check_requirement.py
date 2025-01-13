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

import os
from _plugin import InstallPlugin


def check_requirement(plugin_context, file_map=None, requirement_map=None, *args, **kwargs):
    lib_check = False
    need_libs = set()
    for file_item in file_map.values():
        if file_item.type == InstallPlugin.FileItemType.BIN:
            need_libs.add(requirement_map[file_item.require])
    return plugin_context.return_true(checked=lib_check, requirements=need_libs)
