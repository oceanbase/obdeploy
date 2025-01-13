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
import time
import tempfile
from copy import deepcopy

from ssh import SshClient, SshConfig
from tool import YamlLoader, confirm_port


def health_check(plugin_context, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    deploy_name = plugin_context.deploy_name
    yaml = YamlLoader(stdio)
    targets = plugin_context.get_variable('targets')
    pid_path = plugin_context.get_variable('pid_path')

    stdio.start_loading('obagent program health check')
    time.sleep(1)
    failed = []
    servers = cluster_config.servers
    count = 600
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            stdio.verbose('%s program health check' % server)
            pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
            if pid:
                if confirm_port(client, pid, int(server_config["server_port"])):
                    stdio.verbose('%s obagent[pid: %s] started', server, pid)
                elif count:
                    tmp_servers.append(server)
                else:
                    failed.append('failed to start %s obagent' % server)
            else:
                failed.append('failed to start %s obagent' % server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        plugin_context.return_false()
    else:
        global_config = cluster_config.get_global_conf()
        target_sync_configs = global_config.get('target_sync_configs', [])
        stdio.verbose('start to sync target config')
        data = [{'targets': targets}]
        default_ssh_config = None
        for client in clients.values():
            default_ssh_config = client.config
            break
        for target_sync_config in target_sync_configs:
            host = None
            target_dir = None
            try:
                host = target_sync_config.get('host')
                target_dir = target_sync_config.get('target_dir')
                if not host or not target_dir:
                    continue
                ssh_config_keys = ['username', 'password', 'port', 'key_file', 'timeout']
                auth_keys = ['username', 'password', 'key_file']
                for key in auth_keys:
                    if key in target_sync_config:
                        config = SshConfig(host)
                        break
                else:
                    config = deepcopy(default_ssh_config)
                for key in ssh_config_keys:
                    if key in target_sync_config:
                        setattr(config, key, target_sync_config[key])
                with tempfile.NamedTemporaryFile(suffix='.yaml') as f:
                    yaml.dump(data, f)
                    f.flush()
                    file_name = '{}.yaml'.format(deploy_name or hash(cluster_config))
                    file_path = os.path.join(target_dir, file_name)
                    remote_client = SshClient(config)
                    remote_client.connect(stdio=stdio)
                    remote_client.put_file(f.name, file_path, stdio=stdio)
            except:
                stdio.warn('failed to sync target to {}:{}'.format(host, target_dir))
                stdio.exception('')
        stdio.stop_loading('succeed')
        return plugin_context.return_true(need_bootstrap=False)