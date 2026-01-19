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

import os

from const import STAGE_FIRST
from ssh import LocalClient


def stop(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    server = cluster_config.servers[0]
    server_config = cluster_config.get_server_conf(server)

    bootstrap_path = os.path.join(server_config['home_path'], '.bootstrap')
    cmd = 'ls %s' % bootstrap_path
    if LocalClient.execute_command(cmd):
        workflow.add(STAGE_FIRST, 'parameter_pre', 'generate_env_file', 'get_services_status', 'stop')
    return plugin_context.return_true()