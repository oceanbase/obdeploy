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
    # Stage 15: cluster name (prompt + validate not existing)
    workflow.add(15, 'seekdb_install_cluster_name')
    # Stage 20: get primary candidates
    workflow.add(const.STAGE_SECOND, 'seekdb_install_get_candidates')
    # Stage 40: check primary RPC
    workflow.add(const.STAGE_FOURTH, 'seekdb_install_check_rpc')
    # Stage 70: get resources
    workflow.add(const.STAGE_SEVENTH, 'seekdb_install_get_resources')
    # Stage 90: compute config
    workflow.add(const.STAGE_NINTH, 'seekdb_install_compute_config')
    return plugin_context.return_true()
