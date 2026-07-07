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

from oblogservice_util import check_resource_limits


def resource_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    check_pass = plugin_context.get_variable('check_pass')
    critical = plugin_context.get_variable('critical')
    alert = plugin_context.get_variable('alert')
    get_success = plugin_context.get_variable('get_success')
    running_servers = plugin_context.get_variable('running_servers', default=set()) or set()

    if not check_resource_limits(
        cluster_config,
        clients,
        stdio,
        critical=critical,
        alert=alert,
        check_pass=check_pass,
        skip_servers=running_servers,
    ):
        return plugin_context.return_false()

    if not get_success():
        return plugin_context.return_false()
    return plugin_context.return_true()
