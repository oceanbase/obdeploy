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

from tool import get_option
from _stdio import FormatText

def restore_standby_post(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
    tenant_name = get_option(options, 'tenant')
    cluster_name = plugin_context.cluster_config.deploy_name

    stdio.print(FormatText.success(f'Please execute the command `obd cluster tenant show {cluster_name} -t {tenant_name}` to check standby tenant status'))
    stdio.print(FormatText.info(f'Please execute the command `obd cluster tenant recover {cluster_name} {tenant_name} --unlimited` to enable continuous log synchronization'))
    return plugin_context.return_true()