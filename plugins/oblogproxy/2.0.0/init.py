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

from _errno import EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage, EC_COMPONENT_DIR_NOT_EMPTY


def init(plugin_context, *args, **kwargs):
    def critical(*arg, **kwargs):
        nonlocal global_ret
        global_ret = False
        stdio.error(*arg, **kwargs)

    global_ret = True
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    deploy_name = plugin_context.deploy_name
    stdio = plugin_context.stdio
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    stdio.start_loading('Initializes oblogproxy work home')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        binlog_dir = server_config.get('binlog_dir')
        if not binlog_dir:
            binlog_dir = '%s/run' % home_path
        stdio.verbose('%s init cluster work home', server)
        need_clean = force
        if clean and not force:
            if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                global_ret = False
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True

        if need_clean:
            remote_pid_path = "%s/run/oblogproxy-%s-%s.pid" % (home_path, server.ip, server_config['service_port'])
            remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
            if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
                if client.execute_command('ls /proc/%s/fd' % remote_pid):
                    stdio.verbose('%s oblogproxy[pid:%s] stopping ...' % (server, remote_pid))
                    client.execute_command('kill -9 %s' % remote_pid)
                else:
                    stdio.verbose('failed to stop oblogproxy[pid:%s] in %s, permission deny' % (remote_pid, server))
            else:
                stdio.verbose('%s oblogproxy is not running' % server)
            ret = client.execute_command('rm -fr %s' % home_path, timeout=-1)
            if not ret:
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=ret.stderr))
                continue
        else:
            if client.execute_command('mkdir -p %s' % home_path):
                ret = client.execute_command('ls %s' % (home_path))
                if not ret or ret.stdout.strip():
                    global_ret = False
                    critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=home_path)))
                    critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                    continue
            else:
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=home_path)))

        if not client.execute_command("bash -c 'mkdir -p %s/{log,run}'" % home_path):
            global_ret = False
            stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=home_path)))
        if not client.execute_command("bash -c 'mkdir -p %s'" % binlog_dir):
            global_ret = False
            stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='binlog dir', msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=binlog_dir)))

    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')