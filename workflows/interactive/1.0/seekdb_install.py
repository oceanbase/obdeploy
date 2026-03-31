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


def seekdb_install(plugin_context, workflow, *args, **kwargs):
    # Stage 10: select mode
    workflow.add(const.STAGE_FIRST, 'select_install_mode')
    # Stage 30: select primary cluster (after seekdb stage 20 fills primary_candidates)
    workflow.add(const.STAGE_THIRD, 'select_primary_cluster')
    # Stage 50: rpc action choice (after seekdb stage 40 sets need_rpc_choice)
    workflow.add(const.STAGE_FIFTH, 'rpc_action_choice')
    # Stage 60: base info
    workflow.add(const.STAGE_SIXTH, 'base_info')
    # Stage 80: select run mode (after seekdb stage 70 fills resources)
    workflow.add(const.STAGE_EIGHTH, 'select_run_mode')
    # Stage 100: confirm config (after seekdb stage 90 fills config_list)
    workflow.add(const.STAGE_TENTH, 'seekdb_confirm_config')
    return plugin_context.return_true()
