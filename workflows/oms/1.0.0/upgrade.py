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

from const import STAGE_FIRST


def upgrade(plugin_context, workflow, *args, **kwargs):
    # Both upgrade modes perform their final health check inside upgrade_pre:
    # online upgrade can still roll back there, while offline_upgrade_start
    # includes health_check in its nested workflow. Do not repeat health_check
    # after upgrade_pre has advanced the persisted upgrade index.
    workflow.add(STAGE_FIRST, 'meta_backup', 'generate_oms_config', 'upgrade_pre')
    return plugin_context.return_true()
