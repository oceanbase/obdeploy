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

def create_location_standby_tenant_pre(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if not value:
            value = default
        return value
    
    options = plugin_context.options
    stdio = plugin_context.stdio

    sync_mode = get_option('sync_mode')
    net_timeout = get_option('net_timeout')
    health_check_time = get_option('health_check_time')
    if sync_mode:
        stdio.warn("The current LOCATION mode does not support the '--sync-mode' option.")

    if net_timeout:
        stdio.warn("The current LOCATION mode does not support the '--net-timeout' option.")

    if health_check_time:
        stdio.warn("The current LOCATION mode does not support the 'health-check-time' option.")
    
    return plugin_context.return_true()