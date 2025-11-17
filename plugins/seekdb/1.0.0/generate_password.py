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

import time


def generate_password(plugin_context, return_generate_keys=False, only_generate_password=False, generate_password=True, *args, **kwargs):
    if return_generate_keys:
        generate_keys = []
        if not only_generate_password:
            generate_keys += plugin_context.get_variable('generate_base_keys')
        if generate_password:
            generate_keys += plugin_context.get_variable('generate_password_keys')
        return plugin_context.return_true(generate_keys=generate_keys)

    if generate_password or only_generate_password:
        plugin_context.get_variable('generate_random_password')(**plugin_context.get_variable('generate_random_password_func_params'))
    return plugin_context.return_true()