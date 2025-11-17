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
import os
import time
import hashlib

import requests

from const import TELEMETRY_URL, TELEMETRY_SIG
from tool import docker_run_sudo_prefix, timeout


def get_ips_hash(ips, algorithm='sha256'):
    normalized = ",".join(sorted(ip.strip() for ip in ips.split(",")))
    h = hashlib.new(algorithm)
    h.update(normalized.encode("utf-8"))
    return h.hexdigest()


def start(plugin_context, upgrade=False, web_start=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    for repository in plugin_context.repositories:
        if repository.name == cluster_config.name:
            break
    stdio.start_loading('Start oms')

    global_config = cluster_config.get_global_conf()
    container_name = plugin_context.get_variable('upgrade_container_name') if upgrade else global_config.get('container_name')
    regions_server_map = plugin_context.get_variable('regions_server_map')
    telemetry_post_data = {}
    ips = ''
    for region, servers in regions_server_map.items():
        for server in servers:
            ips += server.ip
            client = clients[server]
            prefix = docker_run_sudo_prefix(client)
            ret = client.execute_command('%sdocker ps -a --filter "name=%s" --format "{{json .}}"' % (prefix ,container_name)).stdout.strip()
            if ret:
                if json.loads(ret).get('State') == 'running':
                    stdio.verbose('%s is runnning, skip' % server)
                    continue
                elif json.loads(ret).get('State') == 'exited':
                    stdio.verbose('%s is exited, start %s' % (server, container_name))
                    if not client.execute_command('%sdocker start %s' % (prefix, container_name)):
                        stdio.error('start %s failed' % container_name)
                        return plugin_context.return_false()
            else:
                image_name = cluster_config.image_name + ':' + repository.version
                server_config = cluster_config.get_server_conf(server)
                https_crt = server_config.get('https_crt')
                https_key = server_config.get('https_key')
                run_path = server_config.get('run_mount_path') or (server_config.get('mount_path') + '/run')
                logs_path = server_config.get('logs_mount_path') or (server_config.get('mount_path') + '/logs')
                store_path = server_config.get('store_mount_path') or (server_config.get('mount_path') + '/store')
                cmd = f"""{prefix}docker run -dit --net host \
                        -v {os.path.join(run_path, 'config.yaml')}:/home/admin/conf/config.yaml \
                        -v {logs_path}:/home/admin/logs \
                        -v {store_path}:/home/ds/store \
                        -v {run_path}:/home/ds/run \
                        {"-v %s:/etc/pki/nginx/oms_server.crt" % https_crt if https_crt else ''}\
                        {"-v %s:/etc/pki/nginx/oms_server.key" % https_key if https_key else ''}\
                        -e OMS_HOST_IP={server.ip} \
                        --privileged=true \
                        --pids-limit -1 \
                        --ulimit nproc=65535:65535 \
                        --name {container_name} \
                        {image_name}"""
                if not client.execute_command(cmd):
                    stdio.stop_loading('fail')
                    stdio.error('%s: start %s failed' % (server, container_name))
                    return plugin_context.return_false()
            time.sleep(60)

    if upgrade:
        cluster_config.update_global_conf('container_name', container_name, True)
    try:
        ips_str = ips
        ip_hash = get_ips_hash(ips_str)
        telemetry_post_data['ip_hash'] = ip_hash
        telemetry_post_data['nodes_num'] = len(cluster_config.servers)
        telemetry_post_data['reporter'] = 'oms_web' if web_start else 'oms'
        telemetry_post_data['version'] = str(cluster_config.tag)
        telemetry_post_data['deploy_time'] = time.strftime("%Y%m%d%H%M%S")
        data = json.dumps(telemetry_post_data, indent=4)
        stdio.verbose('post data: %s' % data)
        with timeout(30):
            requests.post(url=TELEMETRY_URL, \
                          data=json.dumps({'component': 'obd_oms', 'content': data}), \
                          headers={'sig': TELEMETRY_SIG, 'Content-Type': 'application/json'})
    except:
        stdio.verbose('post data failed')

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
