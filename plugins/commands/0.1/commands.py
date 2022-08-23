# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


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
        if ret and ret.stdout:
            results.append([component, server, ret.stdout.strip()])
        elif not no_exception:
            failed = True
        context.update(results=results, failed=failed)
        return plugin_context.return_true(context=context)
