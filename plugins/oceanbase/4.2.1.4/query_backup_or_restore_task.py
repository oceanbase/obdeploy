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

from _errno import EC_OBSHELL_GENERAL_ERROR
from const import TENANT_BACKUP, TENANT_RESTORE


def query_backup_or_restore_task(plugin_context, tenant_name, obshell_clients, task_type, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading("query task of %s tenant %s " % (task_type, tenant_name))

    for client in obshell_clients.values():
        break
    try:
        if task_type == TENANT_RESTORE:
            rv = client.v1.get_tenant_restore_overview(tenant_name)
        elif task_type == TENANT_BACKUP:
            rv = client.v1.get_tenant_backup_overview(tenant_name)
    except Exception as e:
        stdio.stop_loading('fail')
        msg = "Query task of %s %s failed: %s" % (task_type, tenant_name, e.message)
        stdio.error(EC_OBSHELL_GENERAL_ERROR.format(msg=msg))
        return plugin_context.return_false()

    data = [{
        "tenant_id": rv.status['tenant_id'] if task_type == "backup" else rv.tenant_id,
        "start_timestamp": rv.status['start_timestamp'] if task_type == "backup" else rv.start_timestamp,
        "end_timestamp": rv.status['end_timestamp'] if task_type == "backup" else rv.finish_timestamp,
        "status": rv.status['status'] if task_type == "backup" else rv.status,
        "comment": (rv.status['comment'] if task_type == "backup" else rv.comment) or '-'
    }]
    stdio.print_list(data, ['tenant_id', 'start_timestamp', 'end_timestamp', 'task_status', 'comment'],
                     lambda x: [x['tenant_id'], x['start_timestamp'], x['end_timestamp'], x['status'], x['comment']],
                     title="%s task details of %s tenant %s" % (task_type, task_type, tenant_name))

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
