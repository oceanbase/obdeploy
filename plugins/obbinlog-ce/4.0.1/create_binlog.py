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


def create_binlog(plugin_context, ob_deploy, tenant_name,  ob_cluster_repositories, *args, **kwargs):
    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('connect').get_return('binlog_cursor')
    if not cursor:
        stdio.error("tenant_check plugin need binlog_cursor")
        return plugin_context.return_false()

    ob_repository = None
    for repository in ob_cluster_repositories:
        if repository.name in const.COMPS_OB:
            ob_repository = repository
            break
    ob_cluster_config = ob_deploy.deploy_config.components[ob_repository.name]
    ob_global_config = ob_cluster_config.get_global_conf()

    cluster_name = plugin_context.get_variable('cluster_name')
    obconfig_url = plugin_context.get_variable('obconfig_url')
    replicate_num = getattr(plugin_context.options, 'replicate_num')
    sql = f"CREATE BINLOG FOR TENANT `{cluster_name}`.`{tenant_name}` TO USER `cdcro` PASSWORD `{ob_global_config.get('cdcro_password')}` WITH CLUSTER URL `{obconfig_url}`, REPLICATE NUM {replicate_num};"
    try:
        cursor.execute(sql, raise_exception=True)
    except Exception as e:
        stdio.exception(e)
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()

