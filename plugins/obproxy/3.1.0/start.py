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
    cmd = "cat  /proc/net/{tcp,udp} | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
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
    if client.execute_command('cmd=`cat /proc/%s/cmdline`; if [ "$cmd" != "%s" ]; then exit 1; fi' % (pid, command)):
        return True
    return False


def confirm_home_path(client, pid, home_path):
    if client.execute_command('path=`ls -l /proc/%s | grep cwd | awk -F\'-> \' \'{print $2}\'`; if [ "$path" != "%s" ]; then exit 1; fi' % 
        (pid, home_path)):
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

def start(plugin_context, home_path, repository_dir, *args, **kwargs):
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    clusters_cmd = {}
    real_cmd = {}
    pid_path = {}
    remote_bin_path = {}
    need_bootstrap = True
    bin_path = os.path.join(repository_dir, 'bin/obproxy')

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
        remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
        remote_bin_path[server] = bin_path.replace(home_path, remote_home_path)
        server_config = cluster_config.get_server_conf(server)
        pid_path[server] = "%s/run/obproxy-%s-%s.pid" % (server_config['home_path'], server.ip, server_config["listen_port"])

        not_opt_str = [
            'listen_port',
            'prometheus_listen_port',
            'rs_list',
            'cluster_name'
        ]
        get_value = lambda key: "'%s'" % server_config[key] if isinstance(server_config[key], str) else server_config[key]
        opt_str = []
        for key in server_config:
            if key != 'home_path' and key not in not_opt_str:
                value = get_value(key)
                opt_str.append('%s=%s' % (key, value))
        cmd = ['-o %s' % ','.join(opt_str)]
        for key in not_opt_str:
            if key in server_config:
                value = get_value(key)
                cmd.append('--%s %s' % (key, value))
        real_cmd[server] = '%s %s' % (remote_bin_path[server], ' '.join(cmd))
        clusters_cmd[server] = 'cd %s; %s' % (server_config['home_path'], real_cmd[server])

    for server in clusters_cmd:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        port = int(server_config["listen_port"])
        prometheus_port = int(server_config["prometheus_listen_port"])
        stdio.verbose('%s port check' % server)
        remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
        cmd = real_cmd[server].replace('\'', '')
        if remote_pid:
            ret = client.execute_command('cat /proc/%s/cmdline' % remote_pid)
            if ret:
                if ret.stdout.strip() == cmd:
                    continue
                stdio.stop_loading('fail')
                stdio.error('%s:%s port is already used' % (server.ip, port))
                return plugin_context.return_false()

        stdio.verbose('starting %s obproxy', server)
        ret = client.execute_command(clusters_cmd[server])
        if not ret:
            stdio.stop_loading('fail')
            stdio.error('failed to start %s obproxy: %s' % (server, ret.stderr))
            return plugin_context.return_false()
        client.execute_command('''ps -aux | grep '%s' | grep -v grep | awk '{print $2}' > %s''' % (cmd, pid_path[server]))
    stdio.stop_loading('succeed')
        
    stdio.start_loading('obproxy program health check')
    time.sleep(3)
    failed = []
    fail_time = 0
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        stdio.verbose('%s program health check' % server)
        remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
        if remote_pid:
            for pid in remote_pid.split('\n'):
                confirm = confirm_port(client, pid, int(server_config["listen_port"]))
                if confirm:
                    stdio.verbose('%s obproxy[pid: %s] started', server, pid)
                    client.execute_command('echo %s > %s' % (pid, pid_path[server]))
                    break
                else:
                    fail_time += 1
            if fail_time == len(remote_pid.split('\n')):
                failed.append('failed to start %s obproxy' % server)
        else:
            stdio.verbose('No such file: %s' % pid_path[server])
            failed.append('failed to start %s obproxy' % server)
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true(need_bootstrap=True)
