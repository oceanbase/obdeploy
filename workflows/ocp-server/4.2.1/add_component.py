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


def add_component(plugin_context, workflow, *args, **kwargs):
    workflow.add(const.STAGE_FIRST, 'start_check_pre', 'parameter_pre', 'sudo_check', 'password_check', 'tenant_check', 'java_check', 'clockdiff_check', 'tenant_check')

    workflow.add(const.STAGE_SECOND, 'parameter_pre', 'ocp_const', 'cursor_check', 'start', 'health_check', 'bootstrap')

    plugin_context.return_true()
