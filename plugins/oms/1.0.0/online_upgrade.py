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

import datetime
import os.path

import const
from _types import Capacity
from ssh import get_root_permission_client
from tool import get_sudo_prefix, docker_run_sudo_prefix


def online_upgrade(plugin_context, dest_repository, default_oms_files_path=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    global_config = cluster_config.get_global_conf()
    container_name = global_config.get('container_name')

    stdio.start_loading('Start get upgrade script')
    for server in cluster_config.servers:
        client = clients[server]
        if client.config.username == 'root':
            oms_script_path = '/root/oms_script'
        else:
            oms_script_path = f'/home/{client.config.username}/oms_script'
        dest_image_name = cluster_config.image_name + ':' + dest_repository.version
        prefix = docker_run_sudo_prefix(client)
        cp_script_cmd = f"mkdir -p {oms_script_path};{prefix}docker run -d --net host --name oms-config-tool {dest_image_name} bash \
&& {prefix}docker cp oms-config-tool:/root/{const.DDFFI_SCRIPT} {oms_script_path}/ \
&& {prefix}docker cp oms-config-tool:/root/{const.DCDTC_SCRIPT} {oms_script_path}/ \
&& {prefix}docker cp oms-config-tool:/root/{const.DCDR_SCRIPT}  {oms_script_path}/ \
&& {prefix}docker rm -f oms-config-tool"
        if not client.execute_command(cp_script_cmd):
            stdio.stop_loading('fail')
            stdio.error('copy upgrade script to % failed.' % server)
            return plugin_context.return_false()
    stdio.stop_loading('succeed')

    input_path = True
    if default_oms_files_path:
        input_path = False
    oms_files_path = None
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        if not default_oms_files_path:
            if not oms_files_path:
                mount_path = os.path.dirname(server_config.get('logs_mount_path')) if server_config.get('logs_mount_path') else server_config['mount_path']
                default_oms_files_path = oms_files_path or f'{mount_path}/upgrade_docker_files'
            else:
                default_oms_files_path = oms_files_path
        while True:
            if input_path:
                oms_files_path = stdio.read(f'{server.ip}:Please specify a local directory(minimum 20GB) for exporting files from the OMS image. (Default: {default_oms_files_path}): ',blocked=True).strip() or default_oms_files_path
            if not client.execute_command(f"ls {oms_files_path}"):
                client.execute_command(f"mkdir -p {oms_files_path}")
            else:
                stdio.print(f'{oms_files_path} is exist.')
                continue
            if Capacity(client.execute_command(f"df -BG {oms_files_path} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes > 20 << 30:
                break
            stdio.error('The specified directory is too small. Please specify a larger directory.')
        image_name = cluster_config.image_name + ':' + dest_repository.version
        if not client.execute_command(f"ls {oms_script_path}/{const.DDFFI_SCRIPT}"):
            stdio.error('%s: missing script file %s' % (server, const.DDFFI_SCRIPT))
            return plugin_context.return_false()
        client.execute_command(f"rm -rf {oms_files_path}")
        stdio.start_loading('wait dump oms files from image')
        sudo_client = get_root_permission_client(client, server, stdio)
        if not sudo_client:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        prefix = get_sudo_prefix(sudo_client)
        if not sudo_client.execute_command(f'{prefix}sh {oms_script_path}/{const.DDFFI_SCRIPT} {image_name} {oms_files_path}'):
            stdio.stop_loading('fail')
            stdio.error('copy oms files to %s failed.' % server.ip)
            return plugin_context.return_false()
        stdio.stop_loading('succeed')

    stdio.start_loading('Start upgrade oms file')
    container_backup_path = '/home/admin/logs/back' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    dcdtc_servers = []
    for server in cluster_config.servers:
        dcdtc_servers.append(server)
        client = clients[server]
        client.remote_client_get_tpy()
        if not client.execute_command(f"ls {oms_script_path}/{const.DCDTC_SCRIPT}"):
            stdio.stop_loading('fail')
            stdio.error('%s: missing script file %s' % (server, const.DCDTC_SCRIPT))
            return plugin_context.return_false()
        sudo_client = get_root_permission_client(client, server, stdio)
        if not sudo_client:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        prefix = get_sudo_prefix(sudo_client)
        if not client.execute_command(f'{prefix}sh {oms_script_path}/{const.DCDTC_SCRIPT} {container_name} {oms_files_path} {container_backup_path}'):
            stdio.stop_loading('fail')
            rb_failed_servers = []
            for rb_server in dcdtc_servers:
                client = clients[rb_server]
                if not client.execute_command(f"{prefix}sh {oms_script_path}/{const.DCDR_SCRIPT} {container_name} {container_backup_path}"):
                    rb_failed_servers.append(rb_server)
            stdio.error('%s: docker copy dumpfile to container failed. Please contact official technical support.' % server)
            rb_failed_servers and stdio.error('Rollback failed servers: %s.' % rb_failed_servers)
            return plugin_context.return_false()
    stdio.stop_loading('succeed')

    stdio.start_loading('Start upgrade oms')
    for server in cluster_config.servers:
        client = clients[server]
        ret = client.execute_command(f"{prefix}docker exec -it {container_name} /root/docker_hot_update_init.sh")
        if not ret:
            stdio.stop_loading('fail')
            stdio.error('%s: Hot update oms failed. %s' % (server, ret.stderr.strip()))
            return plugin_context.return_false()
        ret = client.execute_command(f"{prefix}docker exec -it {container_name} /root/docker_init.sh")
        if not ret:
            stdio.stop_loading('fail')
            stdio.error('%s: Init oms failed. %s' % (server, ret.stderr.strip()))
            return plugin_context.return_false()
    stdio.stop_loading('succeed')

    return plugin_context.return_true()







