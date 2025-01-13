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
import re

import const
from _rpm import Version


def depends_components_version_check(plugin_context, ob_cluster_repositories, *args, **kwargs):
    def get_subfiles(directory_path):
        ret = client.execute_command('cd %s && ls ' % directory_path)
        subfiles = []
        if ret:
            subfiles = [subfile for subfile in ret.stdout.split('\n') if subfile]
        return subfiles

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    stdio.start_loading('component version check')
    clients = plugin_context.clients

    # check oceanbase verison
    for server in cluster_config.servers:
        home_path = cluster_config.get_server_conf(server)['home_path']
        client = clients[server]
        for repository in ob_cluster_repositories:
            if repository.name in const.COMPS_OB:
                ob_version = repository.version
                break
        else:
            stdio.error(f"The target cluster does not have OceanBase.")
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        if ob_version < Version('4.2.1.0'):
            stdio.error(f"Oceanbase must be version 4.2.1.0 or higher.")
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        sub_dirs = get_subfiles(os.path.join(home_path, 'obcdc'))
        for sub_dir in sub_dirs:
            version = sub_dir.split('-')[2]
            if version[0] == '3':
                continue
            else:
                min_version = Version(version.replace('x', '0'))
                sub_files = get_subfiles(os.path.join(home_path, 'obcdc/%s' % sub_dir))
                for sub_file in sub_files:
                    if sub_file.find(version[:-1]) != -1:
                        max_version = Version(version.replace('x', sub_file.split('.')[-1]))
                        break
                else:
                    stdio.error(f"Can not find the max version of %s" % version)
                    stdio.stop_loading('fail')
                    return plugin_context.return_false()
            if min_version <= ob_version <= max_version:
                break
        else:
            stdio.error(f"The current %s does not support creating task for %s version %s." % (const.COMP_OBBINLOG_CE, repository.name, ob_version))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

    # check proxy version
    for repository in ob_cluster_repositories:
        if repository.name in const.COMPS_ODP:
            if repository.version < Version('4.2.1'):
                stdio.error(f"The version of %s must be greater than 4.2.1" % repository.name)
                stdio.stop_loading('fail')
                return plugin_context.return_false()
            plugin_context.set_variable('proxy_version', repository.version)
            break
    else:
        stdio.error(f"Can not find the proxy component, please check proxy in the deploy.")
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()



