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

def destroy_pre(plugin_context, *args, **kwargs):
    def stop_converter():
        for server in cluster_config.servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            home_path = server_config['home_path']
            binlog_dir = server_config.get('binlog_dir') if server_config.get('binlog_dir') else '{}/run'.format(home_path)
            ret = client.execute_command("ps -aux | grep './binlog_converter' | grep '%s' | grep -v grep | awk '{print $2}'" % binlog_dir)
            if ret and ret.stdout:
                pids = ret.stdout.strip().split('\n')
                for pid in pids:
                    if client.execute_command('ls /proc/%s/fd' % pid):
                        stdio.verbose('%s binlog_converter[pid:%s] stopping ...' % (server, pid))
                        client.execute_command('kill -9 %s' % pid)

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    stdio.start_loading('oblogproxy stop binlog_converter')
    stop_converter()
    stdio.stop_loading('succeed')

    plugin_context.set_variable("clean_dirs", ["binlog_dir"])

    return plugin_context.return_true()