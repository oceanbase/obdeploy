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

from copy import deepcopy
import re
from ssh import LocalClient
from _rpm import Version

import _errno as err
from tool import DirectoryUtil

def pre_check(plugin_context, gather_type=None, utils_work_dir_check=False, *args, **kwargs):

    def utils_work_dir_checker(util_name):
        clients = plugin_context.clients
        cluster_config = plugin_context.cluster_config
        if util_name is None:
            stdio.verbose('util name not provided')
            return False
        for server in cluster_config.servers:
            home_path = cluster_config.get_server_conf(server).get('home_path')
            remote_path = os.path.join(home_path, 'bin')
            software_path = os.path.join(remote_path, util_name)
            client = clients[server]
            stdio.verbose('%s pre check' % (server))
            if not client.execute_command('[ -f %s ]' % software_path):
                stdio.verbose('%s util not exist: %s' % (server, software_path))
                return False
        stdio.stop_loading('succeed')
        return True

    def store_dir_checker_and_handler():
        store_dir_option = getattr(plugin_context.options, 'store_dir', None)
        if (store_dir_option is not None) and (not DirectoryUtil.mkdir(store_dir_option, stdio=stdio)):
            return False
        else:
            return True

    stdio = plugin_context.stdio

    utils_work_dir_check_status = True
    skip = True
    if utils_work_dir_check:
        if gather_type in ['gather_clog', 'gather_slog', 'gather_all']:
            utils_work_dir_check_status = utils_work_dir_checker('ob_admin')
            if gather_type != 'gather_all':
                skip = False
    store_dir_checker_status = store_dir_checker_and_handler()
    checked = utils_work_dir_check_status and store_dir_checker_status
    if checked:
        return plugin_context.return_true(checked = checked, skip = skip)
    else:
        return plugin_context.return_false(checked = checked, skip = skip)

