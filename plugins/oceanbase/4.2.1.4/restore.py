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

import datetime
import time

from obshell import TaskExecuteFailedError
from obshell.model import tenant

from _errno import EC_OBSHELL_GENERAL_ERROR


def restore(plugin_context, tenant_name, obshell_clients, data_backup_uri, archive_log_uri, memory_size, max_cpu, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading(f"Create task of restore tenant {tenant_name} ")

    cursor = plugin_context.get_return('connect').get_return('cursor')
    sql = "select * from oceanbase.DBA_OB_TENANTS where tenant_name = '%s';" % tenant_name
    if cursor.fetchone(sql):
        stdio.stop_loading('fail')
        stdio.error("tenant `%s` is exist" % tenant_name)
        return plugin_context.return_false()

    for obshell_client in obshell_clients.values():
        break
    unit_config_name = 'restore_unit_config' + datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    try:
        obshell_client.v1.create_resource_unit_config(
            unit_config_name,
            memory_size=memory_size,
            max_cpu=int(max_cpu),
            min_cpu=getattr(plugin_context.options, "min_cpu", None),
            max_iops=getattr(plugin_context.options, "max_iops", None),
            min_iops=getattr(plugin_context.options, "min_iops", None),
            log_disk_size=getattr(plugin_context.options, "log_disk_size", None),
        )
    except Exception as e:
        stdio.stop_loading('fail')
        msg = "Restore task of restore %s failed: %s" % (tenant_name, e.message)
        stdio.error(EC_OBSHELL_GENERAL_ERROR.format(msg=msg))
        return plugin_context.return_false()

    zones = getattr(plugin_context.options, "zone", None)
    if not zones:
        cursor = plugin_context.get_return('connect').get_return('cursor')
        sql = "select zone from oceanbase.DBA_OB_ZONES;"
        ret = cursor.fetchall(sql)
        if not ret:
            stdio.stop_loading('fail')
            stdio.error("Query zones failed, please check the cluster status")
            return plugin_context.return_false()
        zones = list(set(row['zone'] for row in ret))
    else:
        zones = zones.split(',')
    zone_list = []
    for zone in zones:
        zone_list.append(tenant.ZoneParam(zone, unit_config_name, plugin_context.options.unit_num, getattr(plugin_context.options, "replica_type", None)),)

    decryption = getattr(plugin_context.options, "decryption", None)
    try:
        ret = obshell_client.v1.post_tenant_restore(
            data_backup_uri=data_backup_uri,
            tenant_name=tenant_name,
            zone_list=zone_list,
            archive_log_uri=archive_log_uri,
            timestamp=getattr(plugin_context.options, "timestamp", None),
            scn=getattr(plugin_context.options, "scn", None),
            ha_high_thread_score=getattr(plugin_context.options, "ha_high_thread_score", None),
            primary_zone=getattr(plugin_context.options, "primary_zone", None),
            concurrency=getattr(plugin_context.options, "concurrency", None),
            decryption=decryption.split(',') if decryption else decryption,
            kms_encrypt_info=getattr(plugin_context.options, "kms_encrypt_info", None)
        )
        stdio.verbose("obshell: restore task dag id %s" % ret.generic_id)
    except Exception as e:
        stdio.stop_loading('fail')
        msg = "Restore task of restore %s failed: %s" % (tenant_name, e.message)
        stdio.error(EC_OBSHELL_GENERAL_ERROR.format(msg=msg))
        return plugin_context.return_false()

    times = 3660
    while True:
        times -= 1
        try:
            obshell_client.v1.get_tenant_restore_overview(tenant_name)
            task_ret = True
            break
        except:
            dag = obshell_client.v1.get_dag(ret.generic_id)
            stdio.verbose("obshell: restore task dag: %s: %s" % (dag.stage, dag.state))
            if dag.is_failed():
                logs = obshell_client.v1._get_failed_dag_last_log(dag)
                task_ret = False
                break
        if times == 0:
            logs = 'times out'
            task_ret = False
            break
        time.sleep(1)
    if not task_ret:
        try:
            obshell_client.v1.operate_dag_sync(ret.generic_id, "ROLLBACK")
        except:
            try:
                obshell_client.v1.operate_dag_sync(ret.generic_id, "PASS")
            except:
                pass

        stdio.stop_loading('fail')
        msg = "Restore task of restore %s failed: %s" % (tenant_name, logs)
        stdio.error(EC_OBSHELL_GENERAL_ERROR.format(msg=msg))
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
