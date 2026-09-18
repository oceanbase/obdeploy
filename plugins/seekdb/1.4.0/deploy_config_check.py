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

from seekdb_14_parameters import get_unsupported_parameters


def deploy_config_check(plugin_context, *args, **kwargs):
    """Reject removed 1.4 settings while the deployment YAML is validated."""
    cluster_config = plugin_context.cluster_config
    errors = []
    for server in cluster_config.servers:
        user_config = cluster_config.get_explicit_server_conf(server)
        legacy_memory_keys, removed_keys = get_unsupported_parameters(user_config)
        if legacy_memory_keys:
            errors.append(
                '[%s] SeekDB 1.4 does not support OBD memory settings %s. '
                'Use `memory_budget` instead.' %
                (server, ', '.join(legacy_memory_keys))
            )
        if removed_keys:
            errors.append(
                '[%s] SeekDB 1.4 removed server parameters %s. Remove or '
                'migrate these settings before deployment.' %
                (server, ', '.join(removed_keys))
            )
    return plugin_context.return_true(errors=errors)
