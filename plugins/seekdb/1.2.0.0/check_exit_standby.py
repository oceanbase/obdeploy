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

from copy import deepcopy
from _stdio import FormatText


def check_exit_standby(plugin_context, standby_clusters, no_primary_cursor=False, relation_deploy_names=[], *args, **kwargs):
    options = plugin_context.options
    stdio = plugin_context.stdio
    ignore_standby = getattr(options, 'ignore_standby', False)
    if not ignore_standby:
        if standby_clusters:
            stdio.warn('Found standby cluster in {0}, drop current cluster will make the standby clusters unavailable'.format(standby_clusters))
            stdio.warn(FormatText.success('Recommendation: you can switchover/decouple the standby cluster then rerun, or rerun with "--ignore-standby" option if you want to proceed despite the risks'))
            stdio.error('Exists standby cluster, current operation is not supported.')
            return
        elif no_primary_cursor and len(relation_deploy_names) > 1:
            relation_deploy_names_cp = deepcopy(relation_deploy_names)
            deploy_name = plugin_context.cluster_config.deploy_name
            stdio.warn('The current cluster is unconnectable, please check if clusters {} use the current cluster as a source by executing command "obd seekdb show {{deployment_name}}" '.format([v for v in relation_deploy_names_cp if v != deploy_name]))
            stdio.warn(FormatText.success('Recommendation: you can failover/decouple the standby cluster then rerun, or rerun with "--ignore-standby" option if you want to proceed despite the risks'))
            stdio.error('There may be standby clusters present, need to confirm.')
            return
    return plugin_context.return_true()
