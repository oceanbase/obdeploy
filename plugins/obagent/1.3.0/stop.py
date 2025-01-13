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

from tool import OrderedDict


stdio = None


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    inode = res.stdout.strip()
    if not res or not inode:
        return False
    stdio.verbose("inode: %s" % inode)
    return inode.split('\n')


def confirm_port(client, pid, port):
    socket_inodes = get_port_socket_inode(client, port)
    if not socket_inodes:
        return False
    ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False
    

def stop(plugin_context, *args, **kwargs):
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    servers = {}
    stdio.start_loading('Stop obagent')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        if 'home_path' not in server_config:
            stdio.verbose('%s home_path is empty', server)
            continue
        home_path = server_config["home_path"]
        agent_processes = OrderedDict()
        agent_processes['obagentd'] = {'path': '%s/run/ob_agentd.pid' % home_path, 'port': None}
        agent_processes['monagent'] = {'path': '%s/run/ob_monagent.pid' % home_path, 'port': server_config['monagent_http_port']}
        agent_processes['mgragent'] = {'path': '%s/run/ob_mgragent.pid' % home_path, 'port': server_config['mgragent_http_port']}
        for agent in agent_processes:
            pid = client.execute_command('cat %s' % agent_processes[agent]['path']).stdout.strip()
            if pid:
                stdio.verbose('%s %s[pid:%s] stopping ...' % (server, agent, pid))
                client.execute_command('kill -9 %s' % pid)
                if server not in servers:
                    servers[server] = {}
                servers[server][agent] = {'pid': pid, 'port': agent_processes[agent]['port'], 'path':  agent_processes[agent]['path']}
            else:
                stdio.verbose('%s %s is not running' % (server, agent))

    count = 10
    time.sleep(1)
    while count and servers:
        tmp_servers = {}
        for server in servers:
            agents_info = servers[server]
            client = clients[server]
            stdio.verbose('%s check whether the port is released' % server)
            for agent in agents_info:
                pid = agents_info[agent]['pid']
                if client.execute_command('ls /proc/%s' % pid) or (agents_info[agent].get('port') and confirm_port(client, pid, agents_info[agent]['port'])):
                    tmp_servers[server] = agents_info
                    break
                client.execute_command('rm -f %s' % agents_info[agent]['path'])
                agents_info[agent] = {}
            else:
                stdio.verbose('%s obagent is stopped', server)
        servers = tmp_servers
        count -= 1
        if count and servers:
            time.sleep(3)

    if servers:
        stdio.stop_loading('fail')
        for server in servers:
            stdio.warn('%s port not released', server)
    else:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()