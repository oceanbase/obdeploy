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


def cancel_backup_or_restore_task(plugin_context, tenant_name, obshell_clients, task_type, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading("Cancel task of %s tenant %s " % (task_type, tenant_name))

    for client in obshell_clients.values():
        break
    try:
        if task_type == TENANT_BACKUP:
            client.v1.patch_tenant_backup_status(tenant_name, 'canceled')
        elif task_type == TENANT_RESTORE:
            client.v1.delete_tenant_restore_sync(tenant_name)
    except Exception as e:
        stdio.stop_loading('fail')
        msg = "Cancel task of restore %s failed: %s" % (tenant_name, e.message)
        stdio.error(EC_OBSHELL_GENERAL_ERROR.format(msg=msg))
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
