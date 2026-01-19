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
import os.path
import time

import const
from _rpm import Version
from ssh import SshClient, SshConfig
from tool import docker_run_sudo_prefix, YamlLoader, Cursor


def get_clients(host, username, password, port, stdio):
    client = SshClient(
        SshConfig(
            host,
            username,
            password,
            None,
            port,
            timeout=10
        ),
        stdio=stdio
    )
    if not client.connect(stdio_func='warn'):
        return None
    return client


def get_takeover_config(plugin_context, ssh_info, container_name, *args, **kwargs):

    def get_mount_paths():
        docker_inspect_info = json.loads(client.execute_command('%sdocker inspect %s --format "{{json .}}"' % (prefix, container_name)).stdout.strip())
        binds = docker_inspect_info['HostConfig']['Binds']
        config_path = run_path = logs_path = store_path = ''
        for path in binds:
            host_path = path.split(':')[0]
            container_path = path.split(':')[1]
            if container_path == '/home/admin/conf/config.yaml':
                config_path = host_path
            elif container_path == '/home/ds/run':
                run_path = host_path
            elif container_path == '/home/admin/logs':
                logs_path = host_path
            elif container_path == '/home/ds/store':
                store_path = host_path
        mount_path = config_path.replace('/run/config.yaml', '') if '/run/config.yaml' in config_path else config_path.replace('/config.yaml', '')
        return config_path, run_path, logs_path, store_path, mount_path

    stdio = plugin_context.stdio
    client = get_clients(ssh_info['host'], ssh_info['username'], ssh_info['password'], ssh_info['port'], stdio)
    if not client:
        stdio.error('Failed to connect to the %s.' % ssh_info['host'])
        error = 'connect info error!'
        return plugin_context.return_false(error=error)

    prefix = docker_run_sudo_prefix(client)
    if not client.execute_command('%sdocker --version' % prefix):
        stdio.error('%s: docker is not installed' % ssh_info['host'])
        error = 'docker is not installed!'
        return plugin_context.return_false(error=error)

    ret = client.execute_command('%sdocker ps -a --filter "name=%s" --format "{{json .}}"' % (prefix, container_name)).stdout.strip()
    if not ret:
        stdio.error('not find container %s' % container_name)
        error = 'not find container %s' % container_name
        return plugin_context.return_false(error=error)

    docker_inspect_info = json.loads(client.execute_command('%sdocker inspect %s --format "{{json .}}"' % (prefix, container_name)).stdout.strip())
    image = docker_inspect_info['Config']['Image']
    if image.find(':') == -1:
        docker_repo_info = client.execute_command('%sdocker images --format "{{json .}}"|grep %s' % (prefix, image))
        for line in docker_repo_info.stdout.strip().splitlines():
            docker_repo_info = json.loads(line)
            image = '%s:%s' % (docker_repo_info['Repository'], docker_repo_info['Tag'])
            break
    image_name = image.split(':')[0]
    image_tag = image.split(':')[1]
    config_mount_path, run_mount_path, logs_mount_path, store_mount_path, mount_path = get_mount_paths()

    global_keys = ['oms_meta_host', 'oms_meta_port', 'oms_meta_user', 'oms_meta_password', 'drc_rm_db', 'drc_cm_db', 'ghana_server_port', 'nginx_server_port', 'cm_server_port',
                   'supervisor_server_port', 'sshd_server_port', 'tsdb_service', 'tsdb_enabled', 'tsdb_url', 'tsdb_password', 'tsdb_username',
                   'apsara_audit_sls_access_key', 'apsara_audit_sls_access_secret', 'apsara_audit_sls_endpoint', 'apsara_audit_sls_ops_site_topic', 'apsara_audit_sls_user_site_topic']

    region_keys = ['cm_url', 'cm_is_default', 'cm_location', 'cm_nodes', 'drc_cm_heartbeat_db', 'cm_region', 'cm_region_cn']
    cluster_config = {}
    yaml = YamlLoader()
    ret = client.execute_command('%sdocker exec -i %s cat /home/admin/conf/config.yaml' % (prefix, container_name))
    if not ret:
        stdio.error(ret.stderr)
        error = ret.stderr
        return plugin_context.return_false(error=error)
    config = yaml.load(ret.stdout.strip())

    try:
        cursor = Cursor(ip=config['oms_meta_host'], user=config['oms_meta_user'], port=int(config['oms_meta_port']), tenant='', password=config['oms_meta_password'], stdio=stdio)
    except Exception as e:
        stdio.error('Failed to connect to the metadb.')
        error = 'Failed to connect to the metadb.'
        return plugin_context.return_false(error=error)

    drc_rm_db = config['drc_rm_db']
    drc_cm_db = config['drc_cm_db']

    regions = []
    cursor.execute('use %s;' % drc_rm_db)
    regions_info = cursor.fetchall('select * from cluster_info;')
    cursor.execute('use %s;' % drc_cm_db)
    cluster_group_info = cursor.fetchall('select id,name from resource_group;')
    all_ips = []
    for row in regions_info:
        region = {}
        region['cm_region'] = row['region']
        region['cm_region_cn'] = row['region_cn']
        region['cm_url'] = row['cm_url']
        region['cm_location'] = row['code']
        region['cm_is_default'] = True if int(row['is_default_cm']) == 1 else False
        for row2 in cluster_group_info:
            if str(row['code']) == str(row2['name']):
                group_id = row2['id']
                break
        ips_info = cursor.fetchall('select resource_group_id,ip from host where resource_group_id = %s;' % group_id)
        ips = [row['ip'] for row in ips_info]
        all_ips.extend(ips)
        all_ips = list(set(all_ips))
        region['cm_nodes'] = ips
        regions.append(region)

    # check nodes ssh login
    clients = []
    failed_ips = []
    for ip in all_ips:
        client = get_clients(ip, ssh_info['username'], ssh_info['password'], ssh_info['port'], stdio)
        if not client:
            failed_ips.append(ip)
        else:
            clients.append(client)
    if failed_ips:
        stdio.error('Failed to connect to the %s.' % ','.join(failed_ips))
        error = 'Failed to connect to the %s.' % ','.join(failed_ips)
        return plugin_context.return_false(error=error)

    # check container name
    for client in clients:
        prefix = docker_run_sudo_prefix(client)
        ret = client.execute_command('%sdocker ps -a --filter "name=%s" --format "{{json .}}"' % (prefix, container_name)).stdout.strip()
        if not ret:
            error = 'OMS multi-node container names must maintain consistency'
            return plugin_context.return_false(error=error)

    # check port and metadb name
    check_keys = ['ghana_server_port', 'nginx_server_port', 'cm_server_port', 'supervisor_server_port', 'sshd_server_port']
    for client in clients:
        if not client.execute_command('ls %s' % config_mount_path):
            stdio.error('OMS multi-node mount_path must maintain consistency.')
            error = 'OMS multi-node mount_path must maintain consistency.'
            return plugin_context.return_false(error=error)
        ct_ret = client.execute_command('%sdocker ps -a --filter "name=%s" --format "{{json .}}"' % (prefix, container_name)).stdout.strip()
        if not ct_ret:
            servers = [client.config.host for client in clients]
            error = f'Please use `docker rename` to rename the OMS container on the node with IPs ({",".join(servers)}) to "{container_name}".'
            stdio.error(error)
            return plugin_context.return_false(error=error)
        ret = client.execute_command('%sdocker exec -i %s cat /home/admin/conf/config.yaml' % (prefix, container_name))
        if not ret:
            stdio.error(ret.stderr)
            error = ret.stderr
            return plugin_context.return_false(error=error)
        node_config = yaml.loads(ret.stdout.strip())
        for key in check_keys:
            if node_config[key] != config[key]:
                stdio.error('OMS multi-node %s must maintain consistency.' % key)
                error = 'OMS multi-node %s must maintain consistency.' % key
                return plugin_context.return_false(error=error)
        node_config_mount_path, node_run_mount_path, node_logs_mount_path, node_store_mount_path, node_mount_path = get_mount_paths()
        if node_mount_path != mount_path:
            stdio.error('OMS multi-node mount_path must maintain consistency.')
            error = 'OMS multi-node mount_path must maintain consistency.'
            return plugin_context.return_false(error=error)
        for region in regions:
            if not region.get('drc_cm_heartbeat_db'):
                if str(region['cm_location']) == str(node_config['cm_location']) and node_config.get('drc_cm_heartbeat_db'):
                    region['drc_cm_heartbeat_db'] = node_config['drc_cm_heartbeat_db']

    # generate cluster config
    cluster_config['user'] = {}
    cluster_config['user']['username'] = ssh_info['username']
    cluster_config['user']['password'] = ssh_info['password']
    cluster_config['user']['port'] = ssh_info['port']
    global_config = {}
    global_config['config_mount_path'] = config_mount_path
    global_config['run_mount_path'] = run_mount_path
    global_config['logs_mount_path'] = logs_mount_path
    global_config['store_mount_path'] = store_mount_path
    global_config['container_name'] = container_name
    cluster_config[const.COMP_OMS_CE] = {}
    oms_config = cluster_config[const.COMP_OMS_CE]
    oms_config["type"] = "docker"
    oms_config["tag"] = image_tag
    if const.COMP_OMS_CE not in image_name and Version(image_tag) < Version('4.2.11'):
        image_name = image_name.replace(const.COMP_OMS, const.COMP_OMS_CE)
    oms_config["image_name"] = image_name
    oms_config['servers'] = all_ips
    settings = {}

    for key, value in config.items():
        if key in global_keys:
            global_config[key] = value
        elif key in region_keys:
            continue
        else:
            settings[key] = value

    global_config['regions'] = regions
    if settings:
        global_config['settings'] = settings
    oms_config['global'] = global_config

    return plugin_context.return_true(cluster_config=cluster_config, servers=','.join(all_ips) if len(all_ips) > 1 else all_ips[0], version=image_tag)
