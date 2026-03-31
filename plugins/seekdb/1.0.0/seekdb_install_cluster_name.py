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

"""SeekDB install: prompt for cluster name (default myseekdb), validate not already existing (allow reuse if status is destroyed); store in seekdb namespace."""

from __future__ import absolute_import, division, print_function

from _deploy import DeployStatus
from tool import InteractiveUI


def seekdb_install_cluster_name(plugin_context, deploy_manager=None, *args, **kwargs):
    if not deploy_manager:
        plugin_context.stdio.error("deploy_manager is required.")
        return plugin_context.return_false()
    stdio = plugin_context.stdio
    options = plugin_context.options
    standby = getattr(options, 'standby', False)
    primary = getattr(options, 'primary', False)
    if standby:
        default_name = "myseekdb_standby"
    elif primary:
        default_name = "myseekdb_primary"
    else:
        default_name = "myseekdb"
    while True:
        name = InteractiveUI.prompt("Instance name", default_name).strip() or default_name
        if not name:
            stdio.warn("Cluster name cannot be empty.")
            continue
        existing = deploy_manager.get_deploy_config(name)
        if existing is not None and existing.deploy_info.status not in [DeployStatus.STATUS_DESTROYED, DeployStatus.STATUS_CONFIGURED]:
            stdio.warn("Cluster name '%s' already exists. Please enter another name." % name)
            continue
        plugin_context.set_variable("cluster_name", name)
        return plugin_context.return_true()
