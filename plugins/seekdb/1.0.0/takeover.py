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

"""Take over a SeekDB instance not deployed by OBD.

Connect to SeekDB, discover ``home_path`` through OBShell's public info API,
bind the response to trusted local processes, then write the cluster config
and deployment metadata.
"""

from __future__ import absolute_import, division, print_function

import os
import re
import shlex

import requests
import yaml
from _deploy import DeployStatus, DeployConfigStatus
from _rpm import Version
from ssh import LocalClient

# Takeover flow depends on OBShell / features aligned with this plugin line.
MIN_SEEKDB_TAKEOVER_VERSION = '1.2.0.0'
COMMON_TAKEOVER_PARAMETERS = [
    'mysql_port', 'data_dir', 'redo_dir', 'datafile_size', 'datafile_maxsize',
    'log_disk_size', 'max_syslog_file_count', 'enable_rpc_service', 'rpc_port',
]


def _query_var(cursor, sql, args=None, default=None):
    """Run sql (fetchone) and return first column value or default."""
    try:
        row = cursor.fetchone(sql, args)
        if row and len(row) >= 1:
            return list(row.values())[0] if hasattr(row, 'values') else row[0]
    except Exception:
        pass
    return default


def _query_obshell_from_ocs(cursor, ip, mysql_port):
    """Keep the established discovery path for SeekDB versions that expose OCS."""
    try:
        row = cursor.fetchone("SHOW DATABASES LIKE 'ocs'")
        if not row:
            return None, None, 'OBShell (ocs database) is not available.'
        row = cursor.fetchone(
            'SELECT home_path, port FROM ocs.all_agent WHERE mysql_port = %s LIMIT 1',
            (int(mysql_port),),
        )
        if not row:
            return None, None, (
                'No OBShell metadata found in ocs.all_agent for %s:%s.'
                % (ip, mysql_port)
            )
        if isinstance(row, dict):
            home_path = row.get('home_path', row.get('HOME_PATH'))
            obshell_port = row.get('port', row.get('PORT'))
        else:
            home_path = row[0] if len(row) > 0 else None
            obshell_port = row[1] if len(row) > 1 else None
        home_path = str(home_path or '').strip()
        if not home_path:
            return None, None, 'OCS returned an empty OBShell home_path.'
        try:
            obshell_port = int(obshell_port)
        except (TypeError, ValueError):
            obshell_port = int(mysql_port) + 5
        return home_path, obshell_port, None
    except Exception as e:
        return None, None, 'Failed to query OBShell metadata from ocs.all_agent: %s' % e


def _command_option(arguments, option):
    """Read a long option from a process command line."""
    prefix = option + '='
    for index, argument in enumerate(arguments):
        if argument == option and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(prefix):
            return argument[len(prefix):]
    return None


def _process_inventory(client):
    """Return process command lines used to correlate OBShell and SeekDB."""
    try:
        result = client.execute_command('ps -eo args')
        if result and getattr(result, 'stdout', None):
            return result.stdout
    except Exception:
        pass
    return ''


def _obshell_port_candidates(process_inventory, mysql_port):
    ports = []
    for line in (process_inventory or '').splitlines():
        try:
            arguments = shlex.split(line)
        except Exception:
            continue
        if not any(os.path.basename(argument) == 'obshell' for argument in arguments):
            continue
        if not any(argument in ('server', 'daemon') for argument in arguments):
            continue
        port = _command_option(arguments, '--port') or _command_option(arguments, '-P')
        try:
            port = int(port)
        except (TypeError, ValueError):
            continue
        if 0 < port <= 65535 and port not in ports:
            ports.append(port)

    # Keep the established defaults as fallbacks when process inspection is
    # restricted.  Interactive installs normally keep the +5 port relation.
    for port in (int(mysql_port) + 5, 2886):
        if 0 < port <= 65535 and port not in ports:
            ports.append(port)
    return ports


def _home_matches_seekdb(process_inventory, home_path, mysql_port):
    portless_home_matches = 0
    for line in (process_inventory or '').splitlines():
        try:
            arguments = shlex.split(line)
        except Exception:
            continue
        if not any(os.path.basename(argument) == 'seekdb' for argument in arguments):
            continue
        port = _command_option(arguments, '--port')
        base_dir = _command_option(arguments, '--base-dir')
        if str(port) == str(mysql_port) and os.path.normpath(base_dir or '') == os.path.normpath(home_path):
            return True
        if port is None and os.path.normpath(base_dir or '') == os.path.normpath(home_path):
            portless_home_matches += 1
    # OBShell starts SeekDB 1.4 with --base-dir but without --port.  The public
    # status endpoint provides the SQL port; process inspection only needs to
    # prove that exactly one visible process owns the returned base directory.
    return portless_home_matches == 1


def _query_home_path_from_obshell(client, ip, mysql_port, stdio):
    """Discover home_path and port through OBShell's public info API."""
    process_inventory = _process_inventory(client)
    candidates = _obshell_port_candidates(process_inventory, mysql_port)
    session = requests.Session()
    # Local management traffic must not be sent through HTTP_PROXY/HTTPS_PROXY.
    session.trust_env = False
    for obshell_port in candidates:
        for scheme in ('http', 'https'):
            url = '%s://%s:%s/api/v1/info' % (scheme, ip, obshell_port)
            try:
                response = session.get(url, timeout=3, verify=False)
                if response.status_code != 200:
                    continue
                payload = response.json()
                data = payload.get('data') or {}
                service_type = str(data.get('type') or '').strip().lower()
                if service_type != 'seekdb':
                    continue
                home_path = str(data.get('homePath') or '').strip()
                if not home_path:
                    continue
                status_url = '%s://%s:%s/api/v1/status' % (
                    scheme, ip, obshell_port)
                status_response = session.get(
                    status_url, timeout=3, verify=False)
                if status_response.status_code != 200:
                    continue
                status_data = status_response.json().get('data') or {}
                sql_port = status_data.get(
                    'sqlPort', status_data.get('sql_port'))
                try:
                    if int(sql_port) != int(mysql_port):
                        continue
                except (TypeError, ValueError):
                    continue
                if _home_matches_seekdb(
                        process_inventory, home_path, mysql_port):
                    return home_path, obshell_port, None
            except Exception:
                continue

    return None, None, (
        'Could not discover the OBShell home_path for seekdb %s:%s. '
        'Ensure OBShell is running on the same host and visible to the SSH user.'
        % (ip, mysql_port)
    )


def _command_stdout(client, command):
    """Execute a remote identity probe and return stripped stdout on success."""
    try:
        result = client.execute_command(command)
    except Exception:
        return None
    if result is None:
        return None
    code = getattr(result, 'code', 0)
    if code not in (None, 0):
        return None
    stdout = getattr(result, 'stdout', None)
    return str(stdout).strip() if stdout is not None else None


def _remote_platform(client):
    platform = _command_stdout(client, 'uname -s')
    return str(platform or '').strip().lower()


def _remote_stat(client, platform, stat_format, path):
    """Read a numeric stat field on GNU/Linux or BSD/macOS."""
    quoted_path = shlex.quote(path)
    if platform == 'linux':
        command = "stat -Lc '%s' -- %s" % (stat_format, quoted_path)
    elif platform == 'darwin':
        # Follow deployment symlinks so this identity is comparable with the
        # executable path reported by lsof for the running process.
        command = "stat -L -f '%s' %s" % (stat_format, quoted_path)
    else:
        return None
    return _command_stdout(client, command)


def _remote_file_identity(client, platform, path):
    return _remote_stat(client, platform, '%d:%i', path)


def _identity_processes(client):
    """Return ``(pid, euid, argv)`` records from the remote host."""
    # ``uid`` is the effective uid on both procps (Linux) and BSD ps (macOS).
    output = _command_stdout(client, 'ps -eo pid= -o uid= -o args=')
    if not output:
        return []
    records = []
    for line in output.splitlines():
        match = re.match(r'^\s*(\d+)\s+(\d+)\s+(.+?)\s*$', line)
        if not match:
            continue
        try:
            arguments = shlex.split(match.group(3))
        except Exception:
            continue
        if arguments:
            records.append((int(match.group(1)), int(match.group(2)), arguments))
    return records


def _process_executable_identity(client, platform, pid):
    if platform == 'linux':
        return _remote_file_identity(
            client, platform, '/proc/%s/exe' % int(pid))
    if platform == 'darwin':
        output = _command_stdout(
            client, 'lsof -a -p %s -d txt -Fn' % int(pid))
        for line in (output or '').splitlines():
            if line.startswith('n') and len(line) > 1:
                return _remote_file_identity(client, platform, line[1:])
    return None


def _process_executable_matches(
        client, platform, pid, expected_identities):
    actual_identity = _process_executable_identity(client, platform, pid)
    return bool(actual_identity and actual_identity in expected_identities)


def _validate_takeover_identity(client, home_path, mysql_port, obshell_port):
    """Bind unauthenticated OBShell metadata to owner-controlled processes.

    The SSH user may only take over a home owned by the same uid.  The OBShell
    and SeekDB processes must also run as that uid and resolve to executable
    inodes exposed by the home.  Requiring the same owner for root avoids
    elevating a user-controlled home through a forged public API response.
    """
    normalized_home = os.path.normpath(str(home_path or '').strip())
    if not os.path.isabs(normalized_home):
        return 'SeekDB takeover home_path must be an absolute path.'

    platform = _remote_platform(client)
    if platform not in ('linux', 'darwin'):
        return 'Unsupported remote platform for SeekDB takeover identity checks.'

    current_uid = _command_stdout(client, 'id -u')
    home_uid = _remote_stat(client, platform, '%u', normalized_home)
    try:
        current_uid = int(current_uid)
        home_uid = int(home_uid)
    except (TypeError, ValueError):
        return 'Could not verify the SeekDB home owner for takeover.'
    if current_uid != home_uid:
        return (
            'SSH user uid %s does not match SeekDB home owner uid %s.'
            % (current_uid, home_uid)
        )

    obshell_executable = _remote_file_identity(
        client, platform, os.path.join(normalized_home, 'bin', 'obshell'))
    database_executables = set(filter(None, (
        _remote_file_identity(
            client, platform, os.path.join(
                normalized_home, 'bin', 'seekdb')),
        _remote_file_identity(
            client, platform, os.path.join(
                normalized_home, 'bin', 'observer')),
    )))
    if not obshell_executable:
        return 'Could not verify the OBShell executable under the takeover home.'
    if not database_executables:
        return 'Could not verify the SeekDB executable under the takeover home.'

    obshell_processes = []
    database_processes = []
    for pid, euid, arguments in _identity_processes(client):
        executable_name = os.path.basename(arguments[0])
        base_dir = _command_option(arguments, '--base-dir')
        port = _command_option(arguments, '--port') or _command_option(
            arguments, '-P')
        if executable_name == 'obshell':
            if not any(arg in ('server', 'daemon') for arg in arguments):
                continue
            if (os.path.normpath(base_dir or '') == normalized_home
                    and str(port) == str(obshell_port)):
                obshell_processes.append((pid, euid))
        elif executable_name in ('seekdb', 'observer'):
            # Existing seekdb.config.bin deployments may start with only
            # ``--port``.  Bind those by owner, executable inode and SQL port;
            # when ``--base-dir`` is present it must match the discovered home.
            if base_dir and os.path.normpath(base_dir) != normalized_home:
                continue
            if ((base_dir and (port is None or str(port) == str(mysql_port)))
                    or (not base_dir and str(port) == str(mysql_port))):
                database_processes.append((pid, euid))

    if not obshell_processes:
        return 'Trusted OBShell process was not found for the takeover home.'
    owner_obshell_processes = [
        pid for pid, euid in obshell_processes if euid == home_uid]
    if not owner_obshell_processes:
        return 'OBShell process owner does not match the SeekDB home owner.'
    if not any(_process_executable_matches(
            client, platform, pid, {obshell_executable})
            for pid in owner_obshell_processes):
        return 'OBShell process executable does not match the takeover home.'

    if not database_processes:
        return 'Trusted SeekDB process was not found for the takeover home.'
    owner_database_processes = [
        pid for pid, euid in database_processes if euid == home_uid]
    if not owner_database_processes:
        return 'SeekDB process owner does not match the takeover home owner.'
    if not any(_process_executable_matches(
            client, platform, pid, database_executables)
            for pid in owner_database_processes):
        return 'SeekDB process executable does not match the takeover home.'
    return None


def _parse_seekdb_version(version_str):
    """Parse SeekDB version from SQL version() string (e.g. ... seekdb-v1.2.0.0 ...) into '1.2.0.0'."""
    if not version_str:
        return None
    match = re.search(r'\bseekdb-v(\d+\.\d+\.\d+\.\d+)(?=\D|$)', str(version_str), re.IGNORECASE)
    return match.group(1) if match else None


def _query_parameters(cursor, names):
    """Read the requested server parameters from V$OB_PARAMETERS in one query."""
    if not names:
        return {}, None
    placeholders = ','.join(['%s'] * len(names))
    sql = (
        'SELECT NAME, VALUE FROM oceanbase.V$OB_PARAMETERS '
        'WHERE NAME IN (%s)' % placeholders
    )
    try:
        rows = cursor.fetchall(sql, tuple(names), raise_exception=True)
    except Exception as e:
        return {}, 'Failed to query SeekDB parameters from V$OB_PARAMETERS: %s' % e
    parameters = {}
    for row in rows or []:
        if isinstance(row, dict):
            name = row.get('NAME', row.get('name'))
            value = row.get('VALUE', row.get('value'))
        else:
            name = row[0] if len(row) > 0 else None
            value = row[1] if len(row) > 1 else None
        if name:
            parameters[str(name)] = value
    return parameters, None


def _complete_storage_paths(config, home_path, version):
    """Fill launch-time storage paths that are not exposed as SQL parameters."""
    if not config.get('data_dir'):
        config['data_dir'] = os.path.join(home_path, 'store')
    if not config.get('redo_dir'):
        config['redo_dir'] = (
            os.path.join(config['data_dir'], 'redo')
            if Version(version) >= Version('1.4.0.0')
            else config['data_dir']
        )


def _takeover_parameter_names(version):
    if Version(version) >= Version('1.4.0.0'):
        memory_parameters = [
            'memory_budget', 'kvcache_memory_limit', 'memstore_memory_limit',
            'vector_memory_limit',
        ]
    else:
        memory_parameters = ['memory_limit', 'memory_hard_limit', 'system_memory']
    return COMMON_TAKEOVER_PARAMETERS + memory_parameters


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

    validate_version = kwargs.get('validate_version')
    if validate_version and not validate_version(version):
        try:
            cursor.close()
        except Exception:
            pass
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

    client = clients.get(server) if clients else None
    home_path = None
    obshell_port = None
    home_path_err = None
    if Version(version) < Version('1.4.0.0'):
        home_path, obshell_port, home_path_err = _query_obshell_from_ocs(
            cursor, ip_val, mysql_port_val)
    if not home_path:
        if client is None:
            stdio.error('SSH client is not available. Cannot discover OBShell home_path.')
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        home_path, obshell_port, http_error = _query_home_path_from_obshell(
            client, ip_val, mysql_port_val, stdio)
        if home_path:
            home_path_err = None
        else:
            home_path_err = http_error or home_path_err
    if home_path_err:
        stdio.error(home_path_err)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    identity_error = _validate_takeover_identity(
        client, home_path, mysql_port_val, obshell_port)
    if identity_error:
        stdio.error(identity_error)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    bin_is_symbolic = False
    if clients and server and server in clients:
        client = clients[server]
        try:
            seekdb_bin = shlex.quote(os.path.join(
                home_path, 'bin', 'seekdb'))
            ret = client.execute_command('[ -L %s ]' % seekdb_bin)
            bin_is_symbolic = ret and getattr(ret, 'code', None) == 0
        except Exception:
            bin_is_symbolic = False


    stdio.stop_loading('succeed')
    stdio.start_loading('Generate config file')

    parameter_names = _takeover_parameter_names(version)
    parameters, parameter_error = _query_parameters(cursor, parameter_names)
    if parameter_error:
        stdio.error(parameter_error)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    global_config = {
        'home_path': home_path,
        'mysql_port': int(parameters.get('mysql_port') or cluster_config.get_server_conf(server).get('mysql_port', 2881)),
        'obshell_port': int(obshell_port),
        'root_password': cluster_config.get_server_conf(server).get('root_password') or '',
    }
    for key in parameter_names:
        if key == 'mysql_port':
            continue
        val = parameters.get(key)
        if val is not None and val != '':
            if key == 'enable_rpc_service':
                global_config[key] = str(val).lower() in ('on', '1', 'true', 'yes')
            elif key == 'max_syslog_file_count':
                try:
                    global_config[key] = int(val)
                except (ValueError, TypeError):
                    pass
            elif key in ('rpc_port', 'mysql_port'):
                try:
                    global_config[key] = int(val)
                except (ValueError, TypeError):
                    pass
            else:
                global_config[key] = val

    _complete_storage_paths(global_config, home_path, version)

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
