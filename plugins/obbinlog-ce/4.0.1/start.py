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

from tool import EnvVariables
from copy import deepcopy
from const import COMP_OBBINLOG


def start(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    binlog_repository = kwargs.get('repository')
    server_pid = {}
    success = True

    stdio.start_loading('start %s' % cluster_config.name)
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        client = clients[server]
        remote_pid_path = "%s/run/%s-%s-%s.pid" % (home_path, cluster_config.name, server.ip, server_config['service_port'])
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                server_pid[server] = remote_pid
                stdio.verbose('%s(%s) is running, skip start' % (cluster_config.name, server))
                continue
        environments = deepcopy(cluster_config.get_environments())
        ret = client.execute_command('cd %s/lib/  &&  ln -sf libstdc++.so.6.0.28 libstdc++.so.6' % home_path)
        if not ret:
            stdio.error("failed to ln lib %s(%s)" % (cluster_config.name, server))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        if 'LD_LIBRARY_PATH' not in environments:
            ld_libary_path = '%s/lib' % home_path
            if binlog_repository.name == COMP_OBBINLOG:
                jvm_path = '%s/lib/jre/lib/%s/server' % (home_path, 'amd64' if binlog_repository.arch == 'x86_64' else 'aarch64')
                ld_libary_path = ":".join([ld_libary_path, jvm_path])
            environments['LD_LIBRARY_PATH'] = ld_libary_path
        with EnvVariables(environments, client):
            client.execute_command("cd {0};nohup {0}/bin/logproxy -f {0}/conf/conf.json > {0}/log/out.log &".format(home_path))
            ret = client.execute_command("ps -aux | grep '%s/bin/logproxy -f %s/conf/conf.json' | grep -v grep | awk '{print $2}'" % (home_path, home_path))
        if not ret:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        server_pid[server] = ret.stdout.strip()
        if not server_pid[server]:
            success = False
            stdio.error("failed to start %s(%s)" % (cluster_config.name, server))
            continue
        client.write_file(server_pid[server], remote_pid_path)
    if success:
        plugin_context.set_variable('server_pid', server_pid)
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')
    return plugin_context.return_false()
