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

from _rpm import Version


def compare(obshell_version, version, op):
    if op == '>':
        return obshell_version > version
    elif op == '<':
        return obshell_version > version
    elif op == '>=':
        return obshell_version >= version
    elif op == '<=':
        return obshell_version <= version
    elif op == '==':
        return obshell_version == version
    elif op == '!=':
        return obshell_version != version
    else:
        return False


def obshell_version_check(plugin_context, version, comparison_operators, obshell_clients, *args, **kwargs):
    stdio = plugin_context.stdio

    stdio.start_loading(f"Check obshell version")
    client = obshell_clients[plugin_context.cluster_config.servers[0].ip]
    try:
        obshell_version_ret = client.v1.get_info()
    except Exception as e:
        stdio.stop_loading('fail')
        stdio.error(e)
        return plugin_context.return_false()
    obshell_version = obshell_version_ret.version.split('-')[0]
    if not compare(obshell_version, Version(version), comparison_operators):
        stdio.stop_loading('fail')
        stdio.error("obshell version(%s) needs %s %s" % (obshell_version, comparison_operators, version))
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
