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

import json
import time
import requests
from urllib.parse import urlparse

from tool import NetUtil


def is_ob_configserver(obconfig_url, stdio):
    parsed_url = urlparse(obconfig_url)
    host = parsed_url.netloc
    stdio.verbose('obconfig_url host: %s' % host)
    url = '%s://%s/debug/pprof/cmdline' % (parsed_url.scheme, host)
    try:
        response = requests.get(url, allow_redirects=False)
        if response.status_code == 404:
            stdio.verbose('request %s status_code: 404' % url)
            return False
    except Exception:
        stdio.verbose('Configserver url check failed: request %s failed' % url)
        return False
    return True


def config_url(ocp_config_server, appname, cid):
    cfg_url = '%s&Action=ObRootServiceInfo&ObCluster=%s' % (ocp_config_server, appname)
    proxy_cfg_url = '%s&Action=GetObProxyConfig&ObRegionGroup=%s' % (ocp_config_server, appname)
    # 清除集群URL内容命令
    cleanup_config_url_content = '%s&Action=DeleteObRootServiceInfoByClusterName&ClusterName=%s' % (
        ocp_config_server, appname)
    # 注册集群信息到Config URL命令
    register_to_config_url = '%s&Action=ObRootServiceRegister&ObCluster=%s&ObClusterId=%s' % (
        ocp_config_server, appname, cid)
    return cfg_url, cleanup_config_url_content, register_to_config_url


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return []
    return res.stdout.strip().split('\n')


def port_release_check(client, pid, port, count):
    socket_inodes = get_port_socket_inode(client, port)
    if not socket_inodes:
        return True
    if count < 5:
        ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
        if ret:
            return not ret.stdout.strip()
        else:
            return not client.execute_command("ls -l /proc/%s" % pid)
    return False


def stop(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_config = cluster_config.get_global_conf()
    appname = global_config['appname'] if 'appname' in global_config else None
    cluster_id = global_config['cluster_id'] if 'cluster_id' in global_config else None
    obconfig_url = global_config['obconfig_url'] if 'obconfig_url' in global_config else None
    stdio.start_loading('Stop observer')
    if obconfig_url and appname and cluster_id:
        if not is_ob_configserver(obconfig_url, stdio):
            try:
                cfg_url, cleanup_config_url_content, register_to_config_url = config_url(obconfig_url, appname, cluster_id)
                stdio.verbose('post %s' % cleanup_config_url_content)
                response = requests.post(cleanup_config_url_content)
                if response.status_code != 200:
                    stdio.warn('%s status code %s' % (cleanup_config_url_content, response.status_code))
            except:
                stdio.warn('failed to clean up the configuration url content')
    servers = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        if 'home_path' not in server_config:
            stdio.verbose('%s home_path is empty', server)
            continue
        remote_pid_path = '%s/run/observer.pid' % server_config['home_path']
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ps uax | egrep " %s " | grep -v grep' % remote_pid):
            stdio.verbose('%s observer[pid:%s] stopping ...' % (server, remote_pid))
            client.execute_command('kill -9 %s' % (remote_pid))
            servers[server] = {
                'client': client,
                'mysql_port': server_config['mysql_port'],
                'rpc_port': server_config['rpc_port'],
                'pid': remote_pid,
                'path': remote_pid_path
            }
        else:
            stdio.verbose('%s observer is not running ...' % server)
    count = 30
    time.sleep(1)
    while count and servers:
        tmp_servers = {}
        for server in servers:
            data = servers[server]
            client = clients[server]
            stdio.verbose('%s check whether the port is released' % server)
            for key in ['rpc_port', 'mysql_port']:
                if data[key] and not port_release_check(data['client'], data['pid'], data[key], count):
                    tmp_servers[server] = data
                    break
                data[key] = ''
            else:
                client.execute_command('rm -f %s' % (data['path']))
                stdio.verbose('%s observer is stopped', server)
        servers = tmp_servers
        count -= 1
        if count and servers:
            if count == 5:
                for server in servers:
                    data = servers[server]
                    server_config = cluster_config.get_server_conf(server)
                    client = clients[server]
                    client.execute_command(
                        "if [[ -d /proc/%s ]]; then pkill -9 -u `whoami` -f '%s/bin/observer -p %s';fi" %
                        (data['pid'], server_config['home_path'], server_config['mysql_port']))
            time.sleep(3)

    if servers:
        stdio.stop_loading('fail')
        for server in servers:
            stdio.warn('%s port not released', server)
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
