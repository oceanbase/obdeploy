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
from _errno import EC_CONFLICT_PORT
from tool import confirm_port


stdio = None


class EnvVariables(object):

    def __init__(self, environments, client):
        self.environments = environments
        self.client = client
        self.env_done = {}

    def __enter__(self):
        for env_key, env_value in self.environments.items():
            self.env_done[env_key] = self.client.get_env(env_key)
            self.client.add_env(env_key, env_value, True)

    def __exit__(self, *args, **kwargs):
        for env_key, env_value in self.env_done.items():
            if env_value is not None:
                self.client.add_env(env_key, env_value, True)
            else:
                self.client.del_env(env_key)


def start(plugin_context,  *args, **kwargs):
    global stdio
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    clusters_cmd = plugin_context.get_variable('clusters_cmd')
    pid_path = plugin_context.get_variable('pid_path')
    real_cmd = plugin_context.get_variable('real_cmd')

    stdio.start_loading('start obproxy')
    for server in clusters_cmd:
        environments = deepcopy(cluster_config.get_environments())
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        port = int(server_config["listen_port"])
        stdio.verbose('%s port check' % server)
        remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
        cmd = real_cmd[server].replace('\'', '')
        if remote_pid:
            ret = client.execute_command('ls /proc/%s/' % remote_pid)
            if ret:
                if confirm_port(client, remote_pid, port):
                    continue
                stdio.stop_loading('fail')
                stdio.error(EC_CONFLICT_PORT.format(server=server.ip, port=port))
                return plugin_context.return_false()

        stdio.verbose('starting %s obproxy', server)
        if 'LD_LIBRARY_PATH' not in environments:
            environments['LD_LIBRARY_PATH'] = '%s/lib:' % server_config['home_path']
        with EnvVariables(environments, client):
            ret = client.execute_command(clusters_cmd[server])
        if not ret:
            stdio.stop_loading('fail')
            stdio.error('failed to start %s obproxy: %s' % (server, ret.stderr))
            return plugin_context.return_false()
        client.execute_command('''ps -aux | grep -e '%s$' | grep -v grep | awk '{print $2}' > %s''' % (cmd, pid_path[server]))
    stdio.stop_loading('succeed')

    return plugin_context.return_true()
