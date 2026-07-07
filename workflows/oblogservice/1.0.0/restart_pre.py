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


def restart_pre(plugin_context, workflow, *args, **kwargs):
    # Override the general restart_pre workflow which schedules `start_check`
    # without first running `start_check_pre`. start_check.py reads `critical`
    # via plugin_context.get_variable(...) — only start_check_pre sets it.
    # Without this override, `obd cluster restart <name>` crashes with
    # `RuntimeError: 'NoneType' object is not callable`.
    #
    # Restart deliberately skips port_check: during restart the cluster's own
    # processes may still own the ports, so `EC_CONFLICT_PORT` would always
    # fire. start_check_pre still runs (with port_check=False) so its callable
    # variables are registered for environment_check / restart_pre downstream.
    # This mirrors oceanbase/3.1.0/restart_pre.py: no `start_check` step.
    #
    # Order:
    #   start_check_pre  -> registers critical/get_success/wait_2_pass/...
    #   environment_check -> directory & permission checks
    #   restart_pre       -> oblogservice-specific marker (need_bootstrap=False)
    workflow.add_with_kwargs(
        STAGE_FIRST,
        {'work_dir_check': True, 'work_dir_empty_check': False, 'port_check': False},
        'start_check_pre',
        'resource_check',
        'environment_check',
        'restart_pre',
    )
    return plugin_context.return_true()
