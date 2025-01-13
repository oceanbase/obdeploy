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


def tenant_check(plugin_context, ob_deploy, tenant_name, ob_cluster_repositories, source_option='create', *args, **kwargs):
    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('target_ob_connect_check').get_return('ob_cursor')
    if not cursor:
        stdio.error("tenant_check plugin need ob_cursor")
        return plugin_context.return_false()

    ob_repository = None
    for repository in ob_cluster_repositories:
        if repository.name in const.COMPS_OB:
            ob_repository = repository
            break
    ob_cluster_config = ob_deploy.deploy_config.components[ob_repository.name]

    stdio.start_loading("Check tenant `%s` " % (tenant_name))
    try:
        ret = cursor.fetchone('show parameters like "cluster";')
        cluster_name = ob_cluster_config.name
        if ret['value'] != ob_cluster_config.name:
            cluster_name = ret['value']
            stdio.verbose("cluster: %s" % cluster_name)
        sql = "select * from oceanbase.DBA_OB_TENANTS where tenant_name = '%s';" % tenant_name
        if not cursor.fetchone(sql):
            stdio.stop_loading('fail')
            stdio.error("tenant `%s` not exist" % tenant_name)
            return plugin_context.return_false()
    except:
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    cursor = plugin_context.get_return('connect').get_return('binlog_cursor')
    if not cursor:
        stdio.stop_loading('fail')
        stdio.error('Failed to get binlog cursor')
        return plugin_context.return_false()
    sql = 'SHOW BINLOG INSTANCES' + f" FOR `{cluster_name}`.`{tenant_name}`"
    ret = cursor.fetchall(sql)
    if len(ret) > 0 and source_option == 'create':
        stdio.stop_loading('fail')
        stdio.error('An instance already exists in cluster tenant, please do not create it again.')
        stdio.print_list(ret, ['name', 'ob_cluster', 'ob_tenant', 'ip', 'port', 'status', 'convert_running'],
                         lambda x: [x['name'], x['ob_cluster'], x['ob_tenant'], x['ip'], x['port'], x['state'], x['convert_running']],
                         title='Binlog Instances List')
        return plugin_context.return_false()

    plugin_context.set_variable('cluster_name', cluster_name)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()

