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


def upload_packages(plugin_context, cursor, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    ob_with_opti_pkgs = plugin_context.get_variable('ob_with_opti_pkgs', default=[])
    for server in servers:
        api_cursor = cursor.get(server)
        for pkg in ob_with_opti_pkgs:
            stdio.verbose('upload package %s' % pkg.file_name)
            if not api_cursor.upload_packages(files={'file': open(pkg.path, 'rb')}, stdio=stdio):
                stdio.error('upload package %s failed' % pkg.file_name)
                continue
        break
    return plugin_context.return_true()
