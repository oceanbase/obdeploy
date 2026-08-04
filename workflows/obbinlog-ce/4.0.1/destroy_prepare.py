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
from _deploy import DeployStatus


def destroy_prepare(plugin_context, workflow, *args, **kwargs):
    component_kwargs = kwargs.get('component_kwargs', {})
    managed_dependencies = [
        component
        for component in (plugin_context.cluster_config.depends or [])
        if component in (plugin_context.components or [])
    ]
    if (
        component_kwargs.get('skip_managed_prepare')
        and managed_dependencies
    ):
        return plugin_context.return_true()

    # Only a RUNNING deployment guarantees that logproxy is online. STOPPED
    # and interrupted UPGRADING deployments start it idempotently, then always
    # stop it through the separate destroy_prepare_cleanup workflow.
    if plugin_context.deploy_status != DeployStatus.STATUS_RUNNING:
        workflow.add(const.STAGE_FIRST, 'start', 'health_check')

    workflow.add(const.STAGE_SECOND, 'connect')
    workflow.add_with_kwargs(
        const.STAGE_SECOND,
        {'show_result': False},
        'get_binlog_instances',
    )
    workflow.add_with_kwargs(
        const.STAGE_SECOND,
        {'no_instance_exit': False, 'source_option': 'stop'},
        'instance_manager',
    )
    return plugin_context.return_true()
