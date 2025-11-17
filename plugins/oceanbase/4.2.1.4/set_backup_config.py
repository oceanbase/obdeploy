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

from obshell import TaskExecuteFailedError

from _errno import EC_OBSHELL_GENERAL_ERROR


def get_all_parent_paths(path):
    path = os.path.abspath(path)
    current_path = path
    parent_paths = []

    while current_path != os.path.dirname(current_path):
        parent_paths.append(current_path)
        current_path = os.path.dirname(current_path)

    parent_paths.append(current_path)
    return parent_paths


def check_nfs_path(paths, client):
    for path in paths:
        ret = client.execute_command('df -T %s | grep nfs' % path)
        if ret and ret.stdout.strip().find(path):
            break
    else:
        return False
    return True


def set_backup_config(plugin_context, tenant_name, obshell_clients,  *args, **kwargs):
    print_flag = False
    def check_uri(uri):
        nonlocal print_flag
        all_path = get_all_parent_paths(uri[len('file://'):])
        for server in plugin_context.cluster_config.servers:
            client = clients[server]
            if not check_nfs_path(all_path, client):
                if len(plugin_context.cluster_config.servers) > 1:
                    not print_flag and stdio.error("data_backup_uri and archive_log_uri on a remote storage medium is a must, Please change the above parameters.")
                    return False
                else:
                    not print_flag and stdio.warn("It is recommended to setup data_backup_uri and archive_log_uri on a remote storage medium.")
                print_flag = True
            return True

    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('connect').get_return('cursor')
    sql = "select * from oceanbase.DBA_OB_TENANTS where tenant_name = '%s';" % tenant_name
    if not cursor.fetchone(sql):
        stdio.error("tenant `%s` not exist" % tenant_name)
        return plugin_context.return_false()
    stdio.start_loading(f"check backup config")
    data_backup_uri = getattr(plugin_context.options, "data_backup_uri")
    archive_log_uri = getattr(plugin_context.options, "archive_log_uri")
    clients = plugin_context.clients
    if (data_backup_uri and data_backup_uri.startswith('file://') and not check_uri(data_backup_uri)) or (archive_log_uri and archive_log_uri.startswith('file://') and not check_uri(archive_log_uri)):
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.start_loading(f"Set backup config")
    for obshell_client in obshell_clients.values():
        break

    try:
        obshell_client.v1.post_tenant_backup_config_sync(
            tenant_name=tenant_name,
            data_base_uri=data_backup_uri,
            archive_base_uri=archive_log_uri,
            log_archive_concurrency=getattr(plugin_context.options, "log_archive_concurrency", -1),
            binding=getattr(plugin_context.options, "binding"),
            ha_low_thread_score=getattr(plugin_context.options, "ha_low_thread_score", -1),
            piece_switch_interval=getattr(plugin_context.options, "piece_switch_interval"),
            archive_lag_target=getattr(plugin_context.options, "archive_lag_target"),
            delete_policy=getattr(plugin_context.options, "delete_policy"),
            delete_recovery_window=getattr(plugin_context.options, "delete_recovery_window")
        )
    except Exception as e:
        if isinstance(e, TaskExecuteFailedError):
            try:
                obshell_client.v1.operate_dag_sync(e.dag.generic_id, "PASS")
            except:
                pass
        stdio.stop_loading('fail')
        msg = "Set backup config failed: %s" % (e.message)
        stdio.error(EC_OBSHELL_GENERAL_ERROR.format(msg=msg))
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
