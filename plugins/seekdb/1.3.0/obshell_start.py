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

"""Start OBShell after SeekDB is up. Reference: OceanBase 4.2.1.4 obshell_start."""

from __future__ import absolute_import, division, print_function

import platform

from _errno import EC_OBSERVER_FAIL_TO_START_OCS
from tool import ConfigUtil
from const import PLATFORM_DARWIN

IS_DARWIN = platform.system() == PLATFORM_DARWIN


def _obshell_process_running(client, obshell_pid_path):
    """Return True if obshell pid exists and process is running."""
    ret = client.execute_command('cat %s' % obshell_pid_path)
    pid = (ret.stdout or '').strip() if ret and getattr(ret, 'stdout', None) else ''
    if not pid:
        return False
    if IS_DARWIN:
        return client.execute_command('ps -p %s' % pid)
    return client.execute_command('ls /proc/%s' % pid)


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
        if _obshell_process_running(client, obshell_pid_path):
            stdio.verbose('%s obshell already started', server)
            continue
        if not client.execute_command('ls %s/bin/obshell' % home_path):
            stdio.warn('%s/bin/obshell does not exist, skip obshell start' % home_path)
            continue
        password = server_config.get('root_password', '')
        client.add_env('OB_ROOT_PASSWORD', password if getattr(client, '_is_local', False) else ConfigUtil.passwd_format(password), True)
        obshell_port = server_config.get('obshell_port', 2886)
        cmd = 'cd %s; %s/bin/obshell admin start --ip %s --base-dir %s --port %s' % (home_path, home_path, server.ip, home_path, obshell_port)
        stdio.verbose('start obshell: %s' % cmd)
        res = client.execute_command(cmd)
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
        if not client.execute_command('ls %s/bin/obshell' % home_path):
            continue
        if _obshell_process_running(client, obshell_pid_path):
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
