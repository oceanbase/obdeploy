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

stdio = None

def check_permission(file_path):
    global stdio
    if not os.path.exists(file_path):
        stdio.error("The file %s does not exist." % file_path)
        return False
    if not os.path.isfile(file_path):
        stdio.error("The %s is not a file." % file_path)
        return False
    if not os.access(file_path, os.R_OK):
        stdio.error("No read permission for file %s." % file_path)
        return False
    return True

def load_license_pre(plugin_context, *args, **kwargs):
    global stdio
    stdio = plugin_context.stdio
    options = plugin_context.options
    license_key_file = getattr(options, "file")
    if not check_permission(license_key_file):
        return plugin_context.return_false()
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        license_file_path = os.path.join(server_config["home_path"], "license.key")
        client = clients[server]
        if not client.put_file(license_key_file, license_file_path, stdio=stdio):
            stdio.error("failed to put {} to {}".format(license_key_file, license_file_path))
            return plugin_context.return_false()
    plugin_context.set_variable("license_file_path", license_file_path)
    return plugin_context.return_true()