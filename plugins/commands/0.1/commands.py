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

try:
    import subprocess32 as subprocess
except:
    import subprocess
import signal
import os

from ssh import LocalClient
from tool import var_replace, COMMAND_ENV


def commands(plugin_context, context, *args, **kwargs):
    def get_value_from_context(key, default=None):
        value = context.get(key, default)
        stdio.verbose('get value from context: %s value %s' % (key, value))
        return value
    
    if plugin_context.get_variable('skip_commands'):
        return plugin_context.return_true()

    stdio = plugin_context.stdio

    command_template = get_value_from_context("command_template")
    command_variables = get_value_from_context("command_variables", {})
    interactive = get_value_from_context("interactive")
    results = get_value_from_context("results", [])
    failed = get_value_from_context("failed", False)
    no_exception = get_value_from_context("no_exception", False)
    no_interruption = get_value_from_context("no_interruption", False)
    executor = get_value_from_context("executor", False)
    component = get_value_from_context("component", False)
    server = get_value_from_context("server", None)
    env = get_value_from_context("env", {})

    cmd = command_template.format(**command_variables)
    cmd = var_replace(cmd, env)
    if interactive:
        if no_interruption:
            stdio.verbose('ctrl c is not accepted in this command')

            def _no_interruption(signum, frame):
                stdio.verbose('ctrl c is not accepted in this command')
            signal.signal(signal.SIGINT, _no_interruption)
        stdio.verbose('exec cmd: {}'.format(cmd))
        subprocess.call(cmd, env=os.environ.copy(), shell=True)
    else:
        client = plugin_context.clients[server]
        if executor == "ssh_client":
            ret = client.execute_command(cmd, stdio=stdio)
        else:
            ret = LocalClient.execute_command(cmd, env=client.env, stdio=stdio)
        if ret and ret.stdout and [component, server, ret.stdout.strip()] not in results:
            results.append([component, server, ret.stdout.strip()])
        elif not no_exception:
            failed = True
        context.update(results=results, failed=failed)
        return plugin_context.return_true()
