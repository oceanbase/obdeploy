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

from ssh import get_root_permission_client, is_root_user
from _errno import EC_OBSERVER_DISABLE_AUTOSTART

def destroy_pre(plugin_context, *args, **kwargs):
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_global_conf()
    appname = global_config['appname']
    stdio = plugin_context.stdio
    auto_service_file = "obd_oceanbase_%s.service" % appname
    for server in cluster_config.servers:
        client = clients[server]
        if client.execute_command("ls /etc/systemd/system/%s" % auto_service_file):
            auto_start_client = get_root_permission_client(client, server, stdio)
            if not auto_start_client:
                stdio.warn("Please check the current user permissions on the %s machine" % server)
                continue
            disable_auto_start_cmd = "systemctl disable"
            remove_cmd = "rm -f /etc/systemd/system/%s" % auto_service_file
            if not is_root_user(auto_start_client):
                disable_auto_start_cmd = f"echo {auto_start_client.config.password} | sudo -S {disable_auto_start_cmd}"
                remove_cmd = f"echo {auto_start_client.config.password} | sudo -S {remove_cmd}"
            if not auto_start_client.execute_command('%s %s' % (disable_auto_start_cmd, auto_service_file)):
                stdio.warn(EC_OBSERVER_DISABLE_AUTOSTART.format(server=server))
            ret = auto_start_client.execute_command(remove_cmd)
            if not ret:
                stdio.warn(f"The deletion of the {auto_service_file} file fails, please manually execute 'sudo rm -f /etc/systemd/system/{auto_service_file}'")

    plugin_context.set_variable("clean_dirs", ['data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir'])

    return plugin_context.return_true()