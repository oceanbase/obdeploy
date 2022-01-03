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

import os
import time


stdio = None


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp,udp}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def confirm_port(client, pid, port):
    socket_inodes = get_port_socket_inode(client, port)
    if not socket_inodes:
        return False
    ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False


def confirm_command(client, pid, command):
    command = command.replace(' ', '').strip()
    if client.execute_command('bash -c \'cmd=`cat /proc/%s/cmdline`; if [ "$cmd" != "%s" ]; then exot 1; fi\'' % (pid, command)):
        return True
    return False


def confirm_home_path(client, pid, home_path):
    if client.execute_command('path=`ls -l /proc/%s | grep cwd | awk -F\'-> \' \'{print $2}\'`; bash -c \'if [ "$path" != "%s" ]; then exit 1; fi\'' % (pid, home_path)):
        return True
    return False


def is_started(client, remote_bin_path, port, home_path, command):
    username = client.config.username
    ret = client.execute_command('pgrep -u %s -f "^%s"' % (username, remote_bin_path))
    if not ret:
        return False
    pids = ret.stdout.strip()
    if not pids:
        return False
    pids = pids.split('\n')
    for pid in pids:
        if confirm_port(client, pid, port):
            break
    else:
        return False
    return confirm_home_path(client, pid, home_path) and confirm_command(client, pid, command)


def obproxyd(home_path, client, ip, port):
    path = os.path.join(os.path.split(__file__)[0], 'obproxyd.sh')
    retmoe_path = os.path.join(home_path, 'obproxyd.sh')
    if os.path.exists(path):
        shell = '''bash %s %s %s %s''' % (retmoe_path, home_path, ip, port)
        return client.put_file(path, retmoe_path) and client.execute_command(shell)
    return False


def start(plugin_context, local_home_path, repository_dir, *args, **kwargs):
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    options = plugin_context.options
    clusters_cmd = {}
    real_cmd = {}
    pid_path = {}
    need_bootstrap = False

    for comp in ['oceanbase', 'oceanbase-ce']:
        if comp in cluster_config.depends:
            root_servers = {}
            ob_config = cluster_config.get_depled_config(comp)
            if not ob_config:
                continue
            odp_config = cluster_config.get_global_conf()
            for server in cluster_config.get_depled_servers(comp):
                config = cluster_config.get_depled_config(comp, server)
                zone = config['zone']
                if zone not in root_servers:
                    root_servers[zone] = '%s:%s' % (server.ip, config['mysql_port'])
            depend_rs_list = ';'.join([root_servers[zone] for zone in root_servers])
            cluster_config.update_global_conf('rs_list', depend_rs_list, save=False)

            config_map = {
                'observer_sys_password': 'proxyro_password',
                'cluster_name': 'appname'
            }
            for key in config_map:
                ob_key = config_map[key]
                if key not in odp_config and ob_key in ob_config:
                    cluster_config.update_global_conf(key, ob_config.get(ob_key), save=False)
            break

    error = False
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        if 'rs_list' not in server_config and 'obproxy_config_server_url' not in server_config:
            error = True
            stdio.error('%s need config "rs_list" or "obproxy_config_server_url"' % server)
    if error:
        return plugin_context.return_false()

    stdio.start_loading('Start obproxy')

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        if not client.execute_command('ls %s/etc/obproxy_config.bin' % home_path):
            need_bootstrap = True
            break

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']

        if client.execute_command("bash -c 'if [ -f %s/bin/obproxy ]; then exit 1; else exit 0; fi;'" % home_path):
            remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
            remote_repository_dir = repository_dir.replace(local_home_path, remote_home_path)
            client.execute_command("bash -c 'mkdir -p %s/{bin,lib}'" % (home_path))
            client.execute_command("ln -fs %s/bin/* %s/bin" % (remote_repository_dir, home_path))
            client.execute_command("ln -fs %s/lib/* %s/lib" % (remote_repository_dir, home_path))

        pid_path[server] = "%s/run/obproxy-%s-%s.pid" % (home_path, server.ip, server_config["listen_port"])

        if getattr(options, 'without_parameter', False) and need_bootstrap is False:
            use_parameter = False
        else:
            use_parameter = True

        if use_parameter:
            not_opt_str = [
                'listen_port',
                'prometheus_listen_port',
                'rs_list',
                'cluster_name'
            ]
            start_unuse = ['home_path', 'observer_sys_password', 'obproxy_sys_password', 'observer_root_password']
            get_value = lambda key: "'%s'" % server_config[key] if isinstance(server_config[key], str) else server_config[key]
            opt_str = ["obproxy_sys_password=e3fd448c516073714189b57233c9cf428ccb1bed"]
            for key in server_config:
                if key not in start_unuse and key not in not_opt_str:
                    value = get_value(key)
                    opt_str.append('%s=%s' % (key, value))
            cmd = ['-o %s' % ','.join(opt_str)]
            for key in not_opt_str:
                if key in server_config:
                    value = get_value(key)
                    cmd.append('--%s %s' % (key, value))
        else:
            cmd = ['--listen_port %s' % server_config.get('listen_port')]

        real_cmd[server] = '%s/bin/obproxy %s' % (home_path, ' '.join(cmd))
        clusters_cmd[server] = 'cd %s; %s' % (home_path, real_cmd[server])

    for server in clusters_cmd:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        port = int(server_config["listen_port"])
        prometheus_port = int(server_config["prometheus_listen_port"])
        stdio.verbose('%s port check' % server)
        remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
        cmd = real_cmd[server].replace('\'', '')
        if remote_pid:
            ret = client.execute_command('ls /proc/%s/' % remote_pid)
            if ret:
                if confirm_port(client, remote_pid, port):
                    continue
                stdio.stop_loading('fail')
                stdio.error('%s:%s port is already used' % (server.ip, port))
                return plugin_context.return_false()

        stdio.verbose('starting %s obproxy', server)
        client.add_env('LD_LIBRARY_PATH', '%s/lib:' % server_config['home_path'], True)
        ret = client.execute_command(clusters_cmd[server])
        client.add_env('LD_LIBRARY_PATH', '', True)
        if not ret:
            stdio.stop_loading('fail')
            stdio.error('failed to start %s obproxy: %s' % (server, ret.stderr))
            return plugin_context.return_false()
        client.execute_command('''ps -aux | grep -e '%s$' | grep -v grep | awk '{print $2}' > %s''' % (cmd, pid_path[server]))
    stdio.stop_loading('succeed')
        
    stdio.start_loading('obproxy program health check')
    failed = []
    servers = cluster_config.servers
    count = 8
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            stdio.verbose('%s program health check' % server)
            remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
            if remote_pid:          
                for pid in remote_pid.split('\n'):
                    confirm = confirm_port(client, pid, int(server_config["listen_port"]))
                    if confirm:
                        proxyd_Pid_path = os.path.join(server_config["home_path"], 'run/obproxyd-%s-%d.pid' % (server.ip, server_config["listen_port"]))
                        if client.execute_command("pid=`cat %s` && ls /proc/$pid" % proxyd_Pid_path):
                            stdio.verbose('%s obproxy[pid: %s] started', server, pid)
                        else:
                            client.execute_command('echo %s > %s' % (pid, pid_path[server]))
                            obproxyd(server_config["home_path"], client, server.ip, server_config["listen_port"])
                            client.execute_command('cat %s | xargs kill -9' % pid_path[server])
                            tmp_servers.append(server)
                        break
                    stdio.verbose('failed to start %s obproxy, remaining retries: %d' % (server, count))
                    if count:
                        tmp_servers.append(server)
                    else:
                        failed.append('failed to start %s obproxy' % server)
            else:
                failed.append('failed to start %s obproxy' % server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true(need_bootstrap=need_bootstrap)
