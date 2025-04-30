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


def scale_out(plugin_context, workflow, *args, **kwargs):
    added_servers = plugin_context.cluster_config.added_servers
    workflow.add_with_kwargs(const.STAGE_FIRST, {'target_servers': added_servers}, 'start_check_pre', 'status_check', 'password_check', 'proxy_id_check', 'status_check',
                 'work_dir_check', 'port_check')

    workflow.add_with_kwargs(const.STAGE_SECOND, {'target_servers': added_servers}, 'parameter_pre', 'start_pre', 'start', 'connect', 'bootstrap')
    plugin_context.return_true()
