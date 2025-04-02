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

import time

from obshell import TaskExecuteFailedError

from _errno import EC_OBSHELL_GENERAL_ERROR
from tool import str2bool


def backup(plugin_context, tenant_name, obshell_clients,  *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading(f"Create task of backup tenant {tenant_name} ")

    cursor = plugin_context.get_return('connect').get_return('cursor')
    sql = "select * from oceanbase.DBA_OB_TENANTS where tenant_name = '%s';" % tenant_name
    if not cursor.fetchone(sql):
        stdio.stop_loading('fail')
        stdio.error("tenant `%s` not exist" % tenant_name)
        return plugin_context.return_false()

    for obshell_client in obshell_clients.values():
        break

    plus_archive = getattr(plugin_context.options, "plus_archive")
    if plus_archive is not None:
        plus_archive = str2bool(plus_archive)

    try:
        ret = obshell_client.v1.start_tenant_backup(
                tenant_name=tenant_name,
                mode=getattr(plugin_context.options, "backup_mode"),
                plus_archive=plus_archive,
                encryption=getattr(plugin_context.options, "encryption")
            )
        stdio.verbose("obshell: backup task dag id %s" % ret.generic_id)
    except Exception as e:
        stdio.stop_loading('fail')
        msg = "Create task of backup %s failed: %s" % (tenant_name, e.message)
        stdio.error(EC_OBSHELL_GENERAL_ERROR.format(msg=msg))
        return plugin_context.return_false()

    times = 3660
    while True:
        times -= 1
        dag = obshell_client.v1.get_dag(ret.generic_id)
        if dag.is_failed():
            logs = obshell_client.v1._get_failed_dag_last_log(dag)
            task_ret = False
            break
        else:
            if dag.nodes[2].state == 'SUCCEED':
                try:
                    obshell_client.v1.get_tenant_backup_overview(tenant_name)
                except:
                    stdio.verbose("wait oceanbase backup task created...")
                else:
                    task_ret = True
                    break
        stdio.verbose("obshell: backup task dag: %s: %s" % (dag.stage, dag.state))
        if times == 0:
            logs = 'times out'
            task_ret = False
            break
        time.sleep(1)
    if not task_ret:
        stdio.stop_loading('fail')
        msg = "Create task of backup %s failed: %s" % (tenant_name, logs)
        stdio.error(EC_OBSHELL_GENERAL_ERROR.format(msg=msg))
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
