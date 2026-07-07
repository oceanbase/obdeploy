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
import re

import shlex

import const
import _errno as err
from _rpm import Version
from _types import Capacity
from tool import confirm_port, get_disk_info

OBLOGSERVICE_MIN_SERVERS = 3
OBLOGSERVICE_OB_MIN_VERSION = Version(const.OBLOGSERVICE_OB_MIN_VERSION)
RESOURCE_DEFAULT_RATIO = 0.8
RESOURCE_WARN_RATIO = 0.9
DEFAULT_MAX_SYSLOG_FILE_COUNT = 4


def get_local_ip(server, server_config):
    return server_config.get('local_ip') or server.ip


def get_cluster_id(cluster_config, server_config):
    if server_config.get('cluster_id') is not None:
        return int(server_config['cluster_id'])
    return int(cluster_config.get_global_conf().get('cluster_id'))


def get_store_dir(home_path):
    return '%s/store' % home_path.rstrip('/')


def _get_mount_path(disk, path):
    while path not in disk and path != '/':
        path = os.path.dirname(path)
    return path


def parse_server_memory_stats(client):
    ret = client.execute_command('cat /proc/meminfo')
    if not ret:
        return None
    memory_key_map = {
        'MemTotal': 'total',
        'MemAvailable': 'available',
        'MemFree': 'free',
    }
    stats = {value: 0 for value in memory_key_map.values()}
    for key, value in re.findall(r'(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
        if key in memory_key_map:
            stats[memory_key_map[key]] = Capacity(str(value)).bytes
    if not stats['available']:
        stats['available'] = stats['free']
    return stats if stats['available'] else None


def get_home_path_disk_avail(client, home_path, stdio):
    mount_path, avail = get_path_disk_avail(client, home_path, stdio)
    return avail


def get_path_disk_avail(client, path, stdio):
    disk = get_disk_info({path}, client, stdio)
    if not disk:
        return None, None
    mount_path = _get_mount_path(disk, path)
    return mount_path, disk.get(mount_path, {}).get('avail')


def get_colocated_ob_cluster_configs(cluster_config):
    deploy_config = cluster_config._deploy_config
    if not deploy_config:
        return []
    configs = []
    for comp_name, comp_config in deploy_config.components.items():
        if comp_name in const.COMPS_OB and cluster_config.name in comp_config.depends:
            configs.append(comp_config)
    return configs


def match_ob_server(ob_cluster_config, logservice_server):
    for server in ob_cluster_config.servers:
        if server.name == logservice_server.name:
            return server
    for server in ob_cluster_config.servers:
        if server.ip == logservice_server.ip:
            return server
    return None


def get_ob_log_disk_path(ob_server_config):
    home_path = ob_server_config['home_path']
    data_path = ob_server_config.get('data_dir') or os.path.join(home_path, 'store')
    redo_dir = ob_server_config.get('redo_dir') or data_path
    return ob_server_config.get('clog_dir') or os.path.join(redo_dir, 'clog')


def check_capacity_usage(
    server,
    key,
    configured_bytes,
    available_bytes,
    resource_label,
    stdio,
    critical=None,
    alert=None,
    check_item=None,
    suggests=None,
    combined=False,
):
    if available_bytes <= 0:
        return True
    ratio = float(configured_bytes) / available_bytes
    if ratio > 1.0:
        if combined:
            message = err.EC_OBLOGSERVICE_COMBINED_RESOURCE_EXCEEDS_AVAILABLE.format(
                server=server,
                key=key,
                configured=format_capacity_bytes(configured_bytes),
                resource=resource_label,
                available=format_capacity_bytes(available_bytes),
            )
        else:
            message = err.EC_OBLOGSERVICE_RESOURCE_EXCEEDS_AVAILABLE.format(
                server=server,
                key=key,
                configured=format_capacity_bytes(configured_bytes),
                resource=resource_label,
                available=format_capacity_bytes(available_bytes),
            )
        if critical and check_item:
            critical(server, check_item, message, suggests or [])
        else:
            stdio.error(message)
        return False
    if ratio > RESOURCE_WARN_RATIO:
        if combined:
            message = err.WC_OBLOGSERVICE_COMBINED_RESOURCE_NEAR_LIMIT.format(
                server=server,
                key=key,
                configured=format_capacity_bytes(configured_bytes),
                resource=resource_label,
                available=format_capacity_bytes(available_bytes),
            )
        else:
            message = err.WC_OBLOGSERVICE_RESOURCE_NEAR_LIMIT.format(
                server=server,
                key=key,
                configured=format_capacity_bytes(configured_bytes),
                resource=resource_label,
                available=format_capacity_bytes(available_bytes),
            )
        if alert and check_item:
            alert(server, check_item, message, suggests or [])
        else:
            stdio.warn(message)
    return True


def build_ip_memory_demand(cluster_config):
    demand = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        memory_limit = resolve_capacity_bytes(cluster_config, server_config, 'memory_limit')
        if memory_limit:
            demand[server.ip] = demand.get(server.ip, 0) + memory_limit
    for ob_cluster_config in get_colocated_ob_cluster_configs(cluster_config):
        for ob_server in ob_cluster_config.servers:
            ob_server_config = ob_cluster_config.get_server_conf_with_default(ob_server)
            ob_memory_limit = resolve_capacity_bytes(
                ob_cluster_config, ob_server_config, 'memory_limit')
            if ob_memory_limit:
                demand[ob_server.ip] = demand.get(ob_server.ip, 0) + ob_memory_limit
    return demand


def build_mount_log_disk_demand(cluster_config, clients, stdio):
    mount_info = {}
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        log_disk_size = resolve_capacity_bytes(cluster_config, server_config, 'log_disk_size')
        if not log_disk_size:
            continue
        home_path = server_config['home_path']
        mount_path, avail = get_path_disk_avail(client, home_path, stdio)
        if mount_path is None or avail is None:
            continue
        # Key by (ip, mount_path) so different machines with the same
        # mount_path string are treated as separate groups.
        key = (server.ip, mount_path)
        info = mount_info.setdefault(
            key,
            {'demand': 0, 'avail': avail, 'servers': [], 'client': client},
        )
        info['demand'] += log_disk_size
        info['servers'].append(server)

    for ob_cluster_config in get_colocated_ob_cluster_configs(cluster_config):
        for ob_server in ob_cluster_config.servers:
            ob_server_config = ob_cluster_config.get_server_conf_with_default(ob_server)
            ob_log_disk_size = resolve_capacity_bytes(
                ob_cluster_config, ob_server_config, 'log_disk_size')
            if not ob_log_disk_size:
                continue
            client = clients.get(ob_server)
            if client is None:
                for server in cluster_config.servers:
                    if server.ip == ob_server.ip:
                        client = clients[server]
                        break
            if client is None:
                continue
            clog_path = get_ob_log_disk_path(ob_server_config)
            mount_path, _ = get_path_disk_avail(client, clog_path, stdio)
            key = (ob_server.ip, mount_path)
            if key not in mount_info:
                continue
            mount_info[key]['demand'] += ob_log_disk_size
    return mount_info


def check_resource_limits(
    cluster_config,
    clients,
    stdio,
    critical=None,
    alert=None,
    check_pass=None,
    skip_servers=None,
):
    skip_servers = skip_servers or set()
    success = True
    ip_memory_demand = build_ip_memory_demand(cluster_config)
    checked_ips = set()
    ip_memory_ok = {}

    for server in cluster_config.servers:
        ip = server.ip
        if ip in checked_ips:
            continue
        checked_ips.add(ip)
        demand = ip_memory_demand.get(ip, 0)
        if not demand:
            ip_memory_ok[ip] = True
            continue
        servers_on_ip = [s for s in cluster_config.servers if s.ip == ip]
        if all(s in skip_servers for s in servers_on_ip):
            ip_memory_ok[ip] = True
            continue
        memory_stats = parse_server_memory_stats(clients[server])
        if not memory_stats:
            if critical:
                critical(
                    server,
                    'memory_limit',
                    err.EC_OBLOGSERVICE_GET_RESOURCE_INFO_FAIL.format(
                        server=server, resource='memory', key='memory_limit'),
                    [],
                )
            else:
                stdio.error(err.EC_OBLOGSERVICE_GET_RESOURCE_INFO_FAIL.format(
                    server=server, resource='memory', key='memory_limit'))
            success = False
            ip_memory_ok[ip] = False
            continue
        ob_cluster_configs = get_colocated_ob_cluster_configs(cluster_config)
        logservice_demand = 0
        for item_server in cluster_config.servers:
            if item_server.ip != ip:
                continue
            item_config = cluster_config.get_server_conf_with_default(item_server)
            logservice_demand += resolve_capacity_bytes(
                cluster_config, item_config, 'memory_limit') or 0
        combined = bool(ob_cluster_configs and demand > logservice_demand)
        ip_memory_ok[ip] = check_capacity_usage(
            server,
            'memory_limit',
            demand,
            memory_stats['available'],
            'memory',
            stdio,
            critical=critical,
            alert=alert,
            check_item='memory_limit',
            combined=combined,
        )
        if not ip_memory_ok[ip]:
            success = False

    mount_info = build_mount_log_disk_demand(cluster_config, clients, stdio)
    checked_mounts = set()
    mount_ok = {}
    for server in cluster_config.servers:
        if server in skip_servers:
            continue
        server_config = cluster_config.get_server_conf_with_default(server)
        if not resolve_capacity_bytes(cluster_config, server_config, 'log_disk_size'):
            continue
        home_path = server_config['home_path']
        mount_path, _ = get_path_disk_avail(clients[server], home_path, stdio)
        if mount_path is None:
            if critical:
                critical(
                    server,
                    'log_disk_size',
                    err.EC_OBLOGSERVICE_GET_RESOURCE_INFO_FAIL.format(
                        server=server, resource='disk', key='log_disk_size'),
                    [],
                )
            else:
                stdio.error(err.EC_OBLOGSERVICE_GET_RESOURCE_INFO_FAIL.format(
                    server=server, resource='disk', key='log_disk_size'))
            success = False
            continue
        key = (server.ip, mount_path)
        if key in checked_mounts:
            continue
        checked_mounts.add(key)
        info = mount_info.get(key)
        if not info:
            mount_ok[key] = True
            continue
        reporter = info['servers'][0]
        logservice_demand = 0
        for item_server in info['servers']:
            item_config = cluster_config.get_server_conf_with_default(item_server)
            logservice_demand += resolve_capacity_bytes(
                cluster_config, item_config, 'log_disk_size') or 0
        combined = bool(get_colocated_ob_cluster_configs(cluster_config)
                        and info['demand'] > logservice_demand)
        mount_ok[key] = check_capacity_usage(
            reporter,
            'log_disk_size',
            info['demand'],
            info['avail'],
            'disk',
            stdio,
            critical=critical,
            alert=alert,
            check_item='log_disk_size',
            combined=combined,
        )
        if not mount_ok[key]:
            success = False

    if check_pass:
        for server in cluster_config.servers:
            if server in skip_servers:
                continue
            server_config = cluster_config.get_server_conf_with_default(server)
            if resolve_capacity_bytes(cluster_config, server_config, 'memory_limit'):
                if ip_memory_ok.get(server.ip, True):
                    check_pass(server, 'memory_limit')
            if resolve_capacity_bytes(cluster_config, server_config, 'log_disk_size'):
                home_path = server_config['home_path']
                mount_path, _ = get_path_disk_avail(clients[server], home_path, stdio)
                key = (server.ip, mount_path)
                if mount_path and mount_ok.get(key, True):
                    check_pass(server, 'log_disk_size')
    return success


def resolve_capacity_bytes(cluster_config, server_config, key):
    value = server_config.get(key)
    if value in (None, 0, '0', '0M'):
        value = cluster_config.get_global_conf().get(key)
    if value in (None, 0, '0', '0M'):
        return None
    return Capacity(value).bytes


def default_capacity_bytes(available):
    return int(available * RESOURCE_DEFAULT_RATIO)


def format_capacity_bytes(size_bytes):
    if size_bytes <= 0:
        return '0M'
    if size_bytes >= Capacity.UNITS['T'] and size_bytes % Capacity.UNITS['T'] == 0:
        return '%dT' % (size_bytes // Capacity.UNITS['T'])
    if size_bytes >= Capacity.UNITS['G']:
        return '%dG' % (size_bytes // Capacity.UNITS['G'])
    if size_bytes >= Capacity.UNITS['M']:
        return '%dM' % (size_bytes // Capacity.UNITS['M'])
    if size_bytes >= Capacity.UNITS['K']:
        return '%dK' % (size_bytes // Capacity.UNITS['K'])
    return '%dB' % size_bytes


def group_servers_by_mount(cluster_config, clients, stdio):
    mount_groups = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        mount_path, avail = get_path_disk_avail(
            clients[server], server_config['home_path'], stdio)
        if mount_path is None or avail is None:
            continue
        # Key by (ip, mount_path) so that different machines sharing the same
        # mount_path string (e.g. "/data/1" on each host) are treated as
        # separate groups. Same-IP multi-node still collapses into one group.
        key = (server.ip, mount_path)
        group = mount_groups.setdefault(key, {'avail': avail, 'servers': []})
        group['servers'].append(server)
    return mount_groups


def is_capacity_configured(cluster_config, key):
    if resolve_capacity_bytes(cluster_config, {}, key):
        return True
    for server in cluster_config.servers:
        value = cluster_config.get_server_conf(server).get(key)
        if value not in (None, 0, '0', '0M'):
            return True
    return False


def apply_default_log_disk_size(cluster_config, clients, stdio):
    if is_capacity_configured(cluster_config, 'log_disk_size'):
        return
    mount_groups = group_servers_by_mount(cluster_config, clients, stdio)
    if not mount_groups:
        return
    min_per_server = None
    for group in mount_groups.values():
        count = len(group['servers'])
        if not count:
            continue
        per_server = int(group['avail'] * RESOURCE_DEFAULT_RATIO / count)
        if min_per_server is None or per_server < min_per_server:
            min_per_server = per_server
    if min_per_server:
        value = format_capacity_bytes(min_per_server)
        # Guard against Capacity integer/T rounding inflating the stored value.
        while Capacity(value).bytes > min_per_server:
            if value.endswith('G'):
                value = '%dM' % (min_per_server // Capacity.UNITS['M'])
                break
            if value.endswith('T'):
                value = '%dG' % (min_per_server // Capacity.UNITS['G'])
                continue
            value = '%dM' % (min_per_server // Capacity.UNITS['M'])
            break
        cluster_config.update_global_conf('log_disk_size', value, False)


def apply_default_memory_limit(cluster_config, clients, stdio):
    if is_capacity_configured(cluster_config, 'memory_limit'):
        return
    ip_groups = {}
    for server in cluster_config.servers:
        memory_stats = parse_server_memory_stats(clients[server])
        if not memory_stats:
            continue
        group = ip_groups.setdefault(server.ip, {
            'avail': memory_stats['available'],
            'servers': [],
        })
        group['servers'].append(server)
    if not ip_groups:
        return
    min_per_server = None
    for group in ip_groups.values():
        count = len(group['servers'])
        if not count:
            continue
        per_server = int(group['avail'] * RESOURCE_DEFAULT_RATIO / count)
        if min_per_server is None or per_server < min_per_server:
            min_per_server = per_server
    if min_per_server:
        cluster_config.update_global_conf(
            'memory_limit', format_capacity_bytes(min_per_server), False)


def build_global_option(cluster_config, server, server_config):
    cluster_id = get_cluster_id(cluster_config, server_config)
    local_ip = get_local_ip(server, server_config)
    rpc_port = int(server_config['port'])
    http_port = int(server_config['http_port'])
    home_path = server_config['home_path']
    store_dir = get_store_dir(home_path)
    options = [
        'cluster_id={cluster_id}'.format(cluster_id=cluster_id),
        'local_ip={local_ip}'.format(local_ip=local_ip),
        'rpc_port={rpc_port}'.format(rpc_port=rpc_port),
        'http_port={http_port}'.format(http_port=http_port),
        'local_storage_dir={store_dir}'.format(store_dir=store_dir),
        'region={region}'.format(region=server_config['region']),
        'az={az}'.format(az=server_config['az']),
    ]
    global_conf = cluster_config.get_global_conf()
    for opt_key in ('memory_limit', 'log_disk_size', 'max_syslog_file_count'):
        value = server_config.get(opt_key)
        if value is None:
            value = global_conf.get(opt_key)
        if value not in (None, 0, '0', '0M'):
            options.append('%s=%s' % (opt_key, value))
    return ', '.join(options)


def pid_path(home_path, local_ip, port):
    return '%s/run/oblogservice-%s-%s.pid' % (home_path, local_ip, port)


def rpc_addr(server, server_config):
    local_ip = get_local_ip(server, server_config)
    return '%s:%d' % (local_ip, int(server_config['port']))


def http_addr(server, server_config):
    local_ip = get_local_ip(server, server_config)
    return '%s:%d' % (local_ip, int(server_config['http_port']))


def get_bootstrap_server(cluster_config):
    global_conf = cluster_config.get_global_conf()
    bootstrap_server = global_conf.get('bootstrap_server')
    if not bootstrap_server:
        return cluster_config.servers[0]
    for server in cluster_config.servers:
        if server.name == bootstrap_server or server.ip == bootstrap_server or str(server) == bootstrap_server:
            return server
    return None


def bootstrap_marker_path(home_path):
    return '%s/run/.bootstrapped' % home_path.rstrip('/')


def should_skip_bootstrap(global_conf):
    if global_conf.get('skip_bootstrap'):
        return True
    object_store_url = (global_conf.get('object_store_url') or '').strip()
    if not object_store_url:
        return True
    placeholders = ('your-bucket', 'your-object-storage-host', 'access_id=xxx', 'access_key=yyy')
    return any(p in object_store_url for p in placeholders)


def validate_oblogservice_oceanbase_combo(components, repositories, stdio):
    """logservice is only supported with oceanbase.ai >= OBLOGSERVICE_OB_MIN_VERSION."""
    if const.COMP_OBLOGSERVICE not in components:
        return True
    ob_components = [name for name in components if name in const.COMPS_OB]
    if not ob_components:
        return True
    repo_map = {repository.name: repository for repository in (repositories or [])}
    min_version = OBLOGSERVICE_OB_MIN_VERSION
    for comp_name in ob_components:
        if comp_name != const.COMP_OB_AI:
            stdio.error(err.EC_OBLOGSERVICE_UNSUPPORTED_OB_TYPE.format(
                min_version=min_version, comp=comp_name
            ))
            return False
        repository = repo_map.get(comp_name)
        if repository is None:
            continue
        if repository.version < min_version:
            stdio.error(err.EC_OBLOGSERVICE_OB_VERSION_TOO_LOW.format(
                min_version=min_version, version=repository.version
            ))
            return False
    return True


def get_running_cluster_id(client, home_path):
    running_option = get_running_global_option(client, home_path)
    if not running_option:
        return None
    match = re.search(r'cluster_id=(\d+)', running_option)
    return int(match.group(1)) if match else None


def normalize_global_option(option_str):
    if not option_str:
        return {}
    result = {}
    for part in option_str.split(','):
        part = part.strip()
        if not part or '=' not in part:
            continue
        key, value = part.split('=', 1)
        result[key.strip()] = value.strip()
    return result


def get_running_global_option(client, home_path):
    ret = client.execute_command(
        "ps -aux | grep '%s/bin/oblogservice -g' | grep -v grep" % home_path
    )
    if not ret or not ret.stdout.strip():
        return None
    line = ret.stdout.strip().split('\n')[0]
    match = re.search(r"-g\s+'([^']+)'", line)
    if not match:
        match = re.search(r'-g\s+"([^"]+)"', line)
    if not match:
        match = re.search(r"-g\s+(\S+)", line)
    return match.group(1) if match else None


def is_oblogservice_running(client, home_path, port, expected_cluster_id):
    running_pid = find_running_pid(client, home_path, port)
    if not running_pid:
        return False
    running_cluster_id = get_running_cluster_id(client, home_path)
    return running_cluster_id == expected_cluster_id


def is_oblogservice_running_with_config(client, home_path, port, expected_option):
    running_pid = find_running_pid(client, home_path, port)
    if not running_pid:
        return False
    running_option = get_running_global_option(client, home_path)
    if not running_option:
        return False
    return normalize_global_option(running_option) == normalize_global_option(expected_option)


def detect_running_servers(cluster_config, clients, stdio=None):
    running_servers = set()
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        client = clients[server]
        home_path = server_config['home_path']
        port = int(server_config['port'])
        if not find_running_pid(client, home_path, port):
            continue
        expected_cluster_id = get_cluster_id(cluster_config, server_config)
        running_cluster_id = get_running_cluster_id(client, home_path)
        if running_cluster_id is not None and running_cluster_id != expected_cluster_id:
            if stdio:
                stdio.verbose(
                    '%s oblogservice is running with a different cluster_id, '
                    'will not skip start check' % server)
            continue
        if stdio:
            stdio.verbose('%s oblogservice is running, skip start check' % server)
        running_servers.add(server)
    return running_servers


def find_running_pid(client, home_path, port):
    ret = client.execute_command(
        "ps -aux | grep '%s/bin/oblogservice -g' | grep -v grep | awk '{print $2}'" % home_path
    )
    if not ret or not ret.stdout.strip():
        return None
    for pid in ret.stdout.strip().split('\n'):
        pid = pid.strip()
        if pid and confirm_port(client, pid, port):
            return pid
    return None


def build_bootstrap_cmd(home_path, http_host, object_store_url, server_specs):
    # object_store_url often contains '&' (query string). Pass via env to avoid
    # the shell splitting it into extra argv entries before ls_ctrl runs.
    # ls_ctrl expects one argv: 'REGION r AZ a SERVER ip:port,REGION ...'
    segments = []
    for region, az, addr in server_specs:
        segments.append(
            'REGION %s AZ %s SERVER %s' % (region, az, addr)
        )
    topology_arg = shlex.quote(','.join(segments))
    return (
        'cd %s && export OBJECT_STORE_URL=%s && '
        './bin/ls_ctrl --host %s bootstrap --object-store-url "${OBJECT_STORE_URL}" %s'
        % (
            shlex.quote(home_path),
            shlex.quote(object_store_url),
            shlex.quote(http_host),
            topology_arg,
        )
    )
