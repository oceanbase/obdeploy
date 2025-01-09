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

from copy import deepcopy

from _errno import EC_OBSERVER_FAIL_TO_START_WITH_ERR
from tool import EnvVariables


def start(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    clusters_cmd = plugin_context.get_variable('clusters_cmd')
    stdio.start_loading('Start observer')
    for server in clusters_cmd:
        environments = deepcopy(cluster_config.get_environments())
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('starting %s observer', server)
        if 'LD_LIBRARY_PATH' not in environments:
            environments['LD_LIBRARY_PATH'] = '%s/lib:' % server_config['home_path']
        with EnvVariables(environments, client):
            ret = client.execute_command(clusters_cmd[server])
        if not ret:
            stdio.stop_loading('fail')
            stdio.error(EC_OBSERVER_FAIL_TO_START_WITH_ERR.format(server=server, stderr=ret.stderr))
            return
    stdio.stop_loading('succeed')

    need_bootstrap = plugin_context.get_variable('need_bootstrap', False)
    stdio.verbose('need_bootstrap: %s' % need_bootstrap)
    return plugin_context.return_true()
