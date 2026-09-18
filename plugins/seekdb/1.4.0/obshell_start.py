# coding: utf-8
# Copyright (c) 2026 OceanBase.
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

"""Start the OBShell bundled with SeekDB 1.4 in SeekDB mode."""

from __future__ import absolute_import, division, print_function

import os
import shlex
import tempfile
import uuid

from _errno import EC_OBSERVER_FAIL_TO_START_OCS
from tool import ConfigUtil


def _obshell_process_running(client, obshell_pid_path, home_path):
    """Return True if the expected SeekDB OBShell process is running."""
    ret = client.execute_command('cat %s' % shlex.quote(obshell_pid_path))
    pid = (ret.stdout or '').strip() if ret and getattr(ret, 'stdout', None) else ''
    if not pid.isdigit():
        return False
    ret = client.execute_command(
        'ps -p %s -o state= -o command=' % shlex.quote(pid))
    process = (ret.stdout or '').strip() if ret and getattr(ret, 'stdout', None) else ''
    if not process:
        return False
    state, _, command = process.partition(' ')
    if state.startswith('Z'):
        return False
    try:
        command_args = shlex.split(command)
    except ValueError:
        return False
    expected_obshell = os.path.normpath(os.path.join(home_path, 'bin', 'obshell'))
    expected_paths = {expected_obshell}
    resolved = client.execute_command(
        'realpath %s' % shlex.quote(expected_obshell))
    resolved_path = (
        (resolved.stdout or '').strip()
        if resolved and getattr(resolved, 'stdout', None) else '')
    if resolved_path:
        expected_paths.add(os.path.normpath(resolved_path))
    if (len(command_args) < 2 or
            os.path.normpath(command_args[0]) not in expected_paths or
            command_args[1] != 'server' or
            '--seekdb' not in command_args):
        return False
    for index, arg in enumerate(command_args):
        if arg == '--base-dir' and index + 1 < len(command_args):
            return command_args[index + 1] == home_path
        if arg.startswith('--base-dir='):
            return arg.split('=', 1)[1] == home_path
    return False


def obshell_start(plugin_context, *args, **kwargs):
    need_bootstrap = plugin_context.get_variable('need_bootstrap')
    start_obshell = plugin_context.get_variable('start_obshell', default=True)
    scale_out = plugin_context.get_variable('scale_out')
    if not start_obshell and not need_bootstrap and not scale_out:
        return plugin_context.return_true()

    stdio = plugin_context.stdio
    stdio.verbose('start_obshell: %s' % start_obshell)
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio.start_loading('obshell start')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        obshell_pid_path = '%s/run/obshell.pid' % home_path
        if _obshell_process_running(client, obshell_pid_path, home_path):
            stdio.verbose('%s obshell already started', server)
            continue
        if not client.execute_command(
                'ls %s/bin/obshell' % shlex.quote(home_path)):
            stdio.error('%s/bin/obshell does not exist' % home_path)
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        password = server_config.get('root_password', '')
        remote_secret_dir = '%s/run/.obd-obshell-secret-%s' % (
            home_path, uuid.uuid4().hex)
        remote_env_path = '%s/password.env' % remote_secret_dir
        quoted_secret_dir = shlex.quote(remote_secret_dir)
        quoted_remote_env = shlex.quote(remote_env_path)
        res = None
        cleanup_succeeded = False
        try:
            if not client.execute_command('mkdir -m 700 %s' % quoted_secret_dir):
                stdio.error('failed to create private OBShell password directory')
            else:
                with tempfile.NamedTemporaryFile(mode='w') as password_file:
                    password_file.write(
                        'export OB_ROOT_PASSWORD=%s\n' % ConfigUtil.passwd_format(password))
                    password_file.flush()
                    os.chmod(password_file.name, 0o600)
                    uploaded = client.put_file(password_file.name, remote_env_path)
                if not uploaded:
                    stdio.error('failed to upload temporary OBShell password file')
                elif not client.execute_command('chmod 600 %s' % quoted_remote_env):
                    stdio.error('failed to protect temporary OBShell password file')
                else:
                    obshell_port = server_config.get('obshell_port', 2886)
                    quoted_home = shlex.quote(home_path)
                    cmd = (
                        '. {env_file} && rm -rf {secret_dir} && '
                        'cd {home} && '
                        '{home}/bin/obshell admin start '
                        '--base-dir {home} --seekdb -P {port}'
                    ).format(
                        env_file=quoted_remote_env,
                        secret_dir=quoted_secret_dir,
                        home=quoted_home,
                        port=shlex.quote(str(obshell_port)),
                    )
                    stdio.verbose('start obshell: %s' % cmd)
                    res = client.execute_command(cmd)
        finally:
            try:
                final_cleanup_succeeded = bool(client.execute_command(
                    'rm -rf %s' % quoted_secret_dir))
            except Exception:
                final_cleanup_succeeded = False
            # A successful start command proves its preceding rm completed.
            cleanup_succeeded = bool(res) or final_cleanup_succeeded
            if not cleanup_succeeded:
                stdio.error('failed to remove temporary OBShell password directory')
        if not cleanup_succeeded:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        if not res:
            stderr = getattr(res, 'stderr', None) if res is not None else None
            if stderr:
                if '[ERROR]' in str(stderr):
                    stdio.print(stderr)
                else:
                    stdio.error(stderr)
            stdio.stop_loading('fail')
            return plugin_context.return_false()
    stdio.stop_loading('succeed')

    failed = []
    stdio.start_loading('obshell program health check')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        obshell_pid_path = '%s/run/obshell.pid' % home_path
        if not client.execute_command(
                'ls %s/bin/obshell' % shlex.quote(home_path)):
            failed.append(EC_OBSERVER_FAIL_TO_START_OCS.format(server=server))
            continue
        if _obshell_process_running(client, obshell_pid_path, home_path):
            stdio.verbose('%s obshell started', server)
        else:
            failed.append(EC_OBSERVER_FAIL_TO_START_OCS.format(server=server))
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
