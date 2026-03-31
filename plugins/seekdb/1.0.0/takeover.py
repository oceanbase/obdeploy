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

"""Take over a SeekDB instance not deployed by OBD: connect, discover config (home_path via OBShell ocs.all_agent), write cluster config and .data."""

from __future__ import absolute_import, division, print_function

import os
import re

import yaml
from _deploy import DeployStatus, DeployConfigStatus
from _rpm import Version
from ssh import LocalClient

# Takeover flow depends on OBShell / features aligned with this plugin line.
MIN_SEEKDB_TAKEOVER_VERSION = '1.2.0.0'


def _query_var(cursor, sql, args=None, default=None):
    """Run sql (fetchone) and return first column value or default."""
    try:
        row = cursor.fetchone(sql, args)
        if row and len(row) >= 1:
            return list(row.values())[0] if hasattr(row, 'values') else row[0]
    except Exception:
        pass
    return default


def _query_home_path_from_obshell(cursor, ip, mysql_port, stdio):
    """Get home_path from OBShell ocs.all_agent (same as OceanBase takeover). Returns (home_path_str, None) or (None, error_msg)."""
    try:
        row = cursor.fetchone("SHOW DATABASES LIKE 'ocs'")
        if not row:
            return None, 'OBShell (ocs database) is not available. Cannot get home_path for takeover.'
        row = cursor.fetchone('SELECT home_path FROM ocs.all_agent WHERE mysql_port = %s LIMIT 1', (int(mysql_port)))
        if row:
            hp = list(row.values())[0] if hasattr(row, 'values') else row[0]
            if hp and str(hp).strip():
                return str(hp).strip(), None
        return None, 'No home_path found in ocs.all_agent for this instance (ip=%s, mysql_port=%s).' % (ip, mysql_port)
    except Exception as e:
        return None, 'Failed to query home_path from OBShell (ocs.all_agent): %s' % e


def _parse_seekdb_version(version_str):
    """Parse SeekDB version from SQL version() string (e.g. ... seekdb-v1.2.0.0 ...) into '1.2.0.0'."""
    if not version_str:
        return None
    s = str(version_str).strip()
    lower = s.lower()
    if 'seekdb-v' in lower:
        idx = lower.index('seekdb-v') + len('seekdb-v')
        rest = s[idx:].strip()
        if not rest:
            return None
        token = rest.split()[0].split('-')[0]
        return token or None
    m = re.search(r'(\d+\.\d+\.\d+\.\d+)', s)
    if m:
        return m.group(1)
    return None


def _show_variable(cursor, name, default=None):
    """Query SHOW VARIABLES LIKE 'name', return Value or default."""
    try:
        row = cursor.fetchone("SHOW VARIABLES LIKE %s", (name,))
        if row:
            v = row.get('Value') if isinstance(row, dict) else (row[1] if len(row) > 1 else None)
            if v is not None:
                return v
    except Exception:
        pass
    return default


def dump_yaml(config, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, 'w') as f:
            f.write(yaml.dump(dict(config), sort_keys=False))
            f.flush()
        return True
    except Exception as e:
        return False


def takeover(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading('Takeover precheck')

    connect_ret = plugin_context.get_return('connect')
    cursor = connect_ret.kwargs.get('cursor') if connect_ret and getattr(connect_ret, 'kwargs', None) else None
    if not cursor:
        stdio.error('Connect failed or cursor not found. Cannot takeover.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    cmds = plugin_context.cmds
    name = cmds[0] if cmds else (getattr(cluster_config, 'deploy_name', None) or 'seekdb')
    obd_home = kwargs.get('obd_home')
    user_config = kwargs.get('user_config')

    if not obd_home:
        stdio.error('obd_home is required for takeover.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    try:
        cursor.execute('select 1', raise_exception=True)
    except Exception as e:
        stdio.error('SeekDB is not available: %s' % e)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    version_str = _query_var(cursor, 'select version() as v', None, None)
    version = _parse_seekdb_version(version_str)
    if not version:
        stdio.error(
            'Could not determine SeekDB version from server (version()=%s). Takeover requires SeekDB %s or later.'
            % (version_str, MIN_SEEKDB_TAKEOVER_VERSION)
        )
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    try:
        if Version(version) < Version(MIN_SEEKDB_TAKEOVER_VERSION):
            stdio.error(
                'SeekDB takeover is not supported for this version (%s). Minimum required: %s.'
                % (version, MIN_SEEKDB_TAKEOVER_VERSION)
            )
            stdio.stop_loading('fail')
            return plugin_context.return_false()
    except Exception:
        stdio.error(
            'Invalid SeekDB version (%s). Takeover requires SeekDB %s or later.'
            % (version, MIN_SEEKDB_TAKEOVER_VERSION)
        )
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    server = cluster_config.servers[0] if cluster_config.servers else None
    if not server:
        stdio.error('No server in cluster config.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    server_conf = cluster_config.get_server_conf(server)
    mysql_port_val = server_conf.get('mysql_port', 2881)
    ip_val = getattr(server, 'ip', None) or (server if isinstance(server, str) else None)
    if not ip_val:
        stdio.error('Could not get server IP from cluster config.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    home_path, home_path_err = _query_home_path_from_obshell(cursor, ip_val, mysql_port_val, stdio)
    if home_path_err:
        stdio.error(home_path_err)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    bin_is_symbolic = False
    if clients and server and server in clients:
        client = clients[server]
        try:
            owner = client.execute_command("ls -ld %s/etc 2>/dev/null | awk '{print $3}'" % home_path.replace("'", "'\\''")).stdout.strip()
            if owner and getattr(client, 'config', None) and getattr(client.config, 'username', None) and owner != client.config.username:
                stdio.warn('SSH user "%s" does not match process owner "%s" for %s. Proceeding anyway.' % (client.config.username, owner, home_path))
        except Exception:
            pass
        try:
            ret = client.execute_command('[ -L "%s/bin/seekdb" ]' % home_path.replace("'", "'\\''"))
            bin_is_symbolic = ret and getattr(ret, 'code', None) == 0
        except Exception:
            bin_is_symbolic = False


    stdio.stop_loading('succeed')
    stdio.start_loading('Generate config file')

    global_config = {
        'home_path': home_path,
        'mysql_port': int(_show_variable(cursor, 'mysql_port') or cluster_config.get_server_conf(server).get('mysql_port', 2881)),
        'root_password': cluster_config.get_server_conf(server).get('root_password') or '',
    }
    for var_name, key in [
        ('data_dir', 'data_dir'),
        ('redo_dir', 'redo_dir'),
        ('memory_limit', 'memory_limit'),
        ('memory_hard_limit', 'memory_hard_limit'),
        ('datafile_size', 'datafile_size'),
        ('datafile_maxsize', 'datafile_maxsize'),
        ('log_disk_size', 'log_disk_size'),
        ('max_syslog_file_count', 'max_syslog_file_count'),
        ('enable_rpc_service', 'enable_rpc_service'),
        ('rpc_port', 'rpc_port'),
    ]:
        val = _show_variable(cursor, var_name)
        if val is not None and val != '':
            if key == 'enable_rpc_service':
                global_config[key] = str(val).lower() in ('on', '1', 'true', 'yes')
            elif key == 'max_syslog_file_count':
                try:
                    global_config[key] = int(val)
                except (ValueError, TypeError):
                    pass
            elif key == 'rpc_port':
                try:
                    global_config[key] = int(val)
                except (ValueError, TypeError):
                    pass
            else:
                global_config[key] = val

    if not global_config.get('data_dir'):
        global_config['data_dir'] = '%s/store' % home_path
    if not global_config.get('redo_dir'):
        global_config['redo_dir'] = '%s/redo' % home_path

    config = {}
    if user_config:
        config['user'] = user_config
    config['seekdb'] = {
        'version': version,
        'servers': [server.ip],
        'global': global_config,
    }

    config_yaml_path = '%s/cluster/%s/config.yaml' % (obd_home, name)
    if not dump_yaml(config, config_yaml_path):
        stdio.error('Failed to write config to %s' % config_yaml_path)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    data = {
        'name': name,
        'components': {'seekdb': {'version': version}},
        'status': DeployStatus.STATUS_CONFIGURED.name,
        'config_status': DeployConfigStatus.UNCHNAGE.name,
    }
    data_path = '%s/cluster/%s/.data' % (obd_home, name)
    if not dump_yaml(data, data_path):
        LocalClient.execute_command('rm -rf %s' % config_yaml_path)
        stdio.error('Failed to write .data to %s' % data_path)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    inner_server_key = server.name
    inner_config = {
        'seekdb': {inner_server_key: {}},
        '$_deploy_install_mode': 'ln' if bin_is_symbolic else 'cp',
    }
    inner_config_path = '%s/cluster/%s/inner_config.yaml' % (obd_home, name)
    if not dump_yaml(inner_config, inner_config_path):
        LocalClient.execute_command('rm -rf %s %s' % (config_yaml_path, data_path))
        stdio.error('Failed to write inner_config.yaml to %s' % inner_config_path)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    try:
        cursor.close()
    except Exception:
        pass

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
