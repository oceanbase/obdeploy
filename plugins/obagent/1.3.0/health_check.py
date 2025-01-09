# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


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
    start_env = plugin_context.get_variable('start_env')

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
            server_config = start_env[server]
            home_path = server_config['home_path']
            stdio.verbose('%s program health check' % server)
            pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
            if pid:
                mgr_pid = client.execute_command("cat %s" % os.path.join(home_path, 'run/ob_mgragent.pid')).stdout.strip()
                if mgr_pid and confirm_port(client, mgr_pid, int(server_config["mgragent_http_port"])):
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
                    remote_client.connect()
                    remote_client.put_file(f.name, file_path)
            except:
                stdio.warn('failed to sync target to {}:{}'.format(host, target_dir))
                stdio.exception('')
        stdio.stop_loading('succeed')
        return plugin_context.return_true(need_bootstrap=False)