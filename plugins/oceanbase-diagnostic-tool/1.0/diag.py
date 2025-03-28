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
from ssh import LocalClient
import _errno as err


def diag(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    obdiag_install_dir=kwargs.get("repository").repository_dir
    obdiag_bin = "obdiag"

    def local_execute_command(command, env=None, timeout=None):
        exec_command = r"{install_dir}/{cmd}".format(install_dir=obdiag_install_dir, cmd=command)
        return LocalClient.execute_command(exec_command, env, timeout, stdio)

    ret = local_execute_command(f'{obdiag_bin} {" ".join(kwargs["full_cmd"])}')
    if not ret:
        stdio.error(err.EC_OBDIAG_NOT_FOUND.format())
        return plugin_context.return_false()
    stdio.print(ret.stdout)
