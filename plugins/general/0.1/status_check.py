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

from _deploy import ClusterStatus


def status_check(plugin_context, target_status=ClusterStatus.STATUS_RUNNING, is_error=False, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    cluster_status = plugin_context.get_return('status').get_return('cluster_status')
    print_msg = stdio.error if is_error else stdio.warn
    status_msg = 'running' if target_status == ClusterStatus.STATUS_RUNNING else 'stopped'
    status_check_pass = True
    for server in cluster_status:
        if cluster_status[server] != target_status.value:
            status_check_pass = False
            print_msg("%s %s is not %s" % (server, cluster_config.name, status_msg))

    if status_check_pass:
        return plugin_context.return_true(status_check_pass=status_check_pass)
    return plugin_context.return_false(status_check_pass=status_check_pass)
