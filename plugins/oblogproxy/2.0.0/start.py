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

import json
import os
import re
import time
from copy import deepcopy

from tool import FileUtil


def get_port_socket_inode(client, port, stdio):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def confirm_port(client, pid, port, stdio):
    socket_inodes = get_port_socket_inode(client, port, stdio)
    if not socket_inodes:
        return False
    ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False


def is_started(client, port, remote_pid_path, home_path, stdio):
    ret = client.execute_command("ps -aux | grep '{0}/bin/logproxy -f {0}/conf/conf.json' | grep -v grep | awk '{print $2}' ".format(home_path))
    if not ret:
        return False
    pids = ret.stdout.strip()
    if not pids:
        return False
    pids = pids.split('\n')
    for pid in pids:
        if confirm_port(client, pid, port, stdio):
            client.execute_command('echo "%s" > %s' % (pid, remote_pid_path))
            return True
    else:
        return False


def prepare_conf(repositories, cluster_config, clients, stdio):
    # depends config
    cdcro_password = None
    ob_sys_username = None

    for comp in ["oceanbase", "oceanbase-ce"]:
        if comp in cluster_config.depends:
            observer_globals = cluster_config.get_depend_config(comp)
            cdcro_password = observer_globals.get('cdcro_password')
            ob_sys_username = 'cdcro'
            break

    repository_dir = None
    for repository in repositories:
        if repository.name == cluster_config.name:
            repository_dir = repository.repository_dir
            break
    with FileUtil.open(os.path.join(repository_dir, 'conf/conf.json')) as f:
        config = json.load(f)

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        config['oblogreader_path'] = '{}/run'.format(home_path)
        custom_config = cluster_config.get_server_conf(server)
        config.update(custom_config)
        home_path = custom_config['home_path']
        ob_sys_username = ob_sys_username if ob_sys_username is not None else custom_config.get('ob_sys_username')
        config['ob_sys_username'] = client.execute_command("{}/bin/logproxy -x {}".format(home_path, ob_sys_username)).stdout.strip() if ob_sys_username else ""
        ob_sys_password = cdcro_password if cdcro_password is not None else custom_config.get('ob_sys_password')
        config['ob_sys_password'] = client.execute_command("{}/bin/logproxy -x {}".format(home_path, ob_sys_password)).stdout.strip() if ob_sys_password else ""
        config['binlog_log_bin_basename'] = custom_config.get('binlog_dir') if custom_config.get('binlog_dir') else '%s/run' % home_path
        if not custom_config.get('binlog_obcdc_ce_path_template'):
            source_binlog_path = config['binlog_obcdc_ce_path_template']
            config['binlog_obcdc_ce_path_template'] = os.path.join(home_path, source_binlog_path[source_binlog_path.find('/obcdc/') + 1:])
        if not custom_config.get('oblogreader_obcdc_ce_path_template'):
            source_oblogreader_path = config['oblogreader_obcdc_ce_path_template']
            config['oblogreader_obcdc_ce_path_template'] = os.path.join(home_path, source_oblogreader_path[source_oblogreader_path.find('/obcdc/') + 1:])
        if not custom_config.get('bin_path'):
            config['bin_path'] = '{}/bin'.format(home_path)
        if not custom_config.get('oblogreader_path'):
            config['oblogreader_path'] = '{}/run'.format(home_path)

        if 'binlog_dir' in config:
            config.pop('binlog_dir')
        config.pop('home_path')
        json_config = json.dumps(config, indent=4)
        conf_path = '{}/conf/conf.json'.format(home_path)
        if not client.write_file(json_config, conf_path):
            stdio.error('failed to write config file {}'.format(conf_path))
            return False
    return True


def start(plugin_context, start_env=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    stdio.start_loading('start oblogproxy')

    if not start_env:
        start_env = prepare_conf(plugin_context.repositories, cluster_config, clients, stdio)
        if not start_env:
            return plugin_context.return_false()

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        client = clients[server]
        remote_pid_path = "%s/run/oblogproxy-%s-%s.pid" % (home_path, server.ip, server_config['service_port'])
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                continue

        client.execute_command("cd {0}; {0}/bin/logproxy -f {0}/conf/conf.json &>{0}/log/out.log & echo $! > {1}".format(home_path, remote_pid_path))
    servers = cluster_config.servers
    count = 60
    failed = []
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            stdio.verbose('%s program health check' % server)
            remote_pid_path = "%s/run/oblogproxy-%s-%s.pid" % (server_config['home_path'], server.ip, server_config['service_port'])
            remote_pid = client.execute_command("cat %s" % remote_pid_path).stdout.strip()
            if remote_pid:
                for pid in re.findall('\d+', remote_pid):
                    confirm = confirm_port(client, pid, int(server_config["service_port"]), stdio)
                    if confirm:
                        if client.execute_command("ls /proc/%s" % remote_pid):
                            stdio.verbose('%s oblogproxy[pid: %s] started', server, pid)
                        else:
                            tmp_servers.append(server)
                        break
                    stdio.verbose('failed to start %s oblogproxy, remaining retries: %d' % (server, count))
                    if count:
                        tmp_servers.append(server)
                    else:
                        failed.append('failed to start %s oblogproxy' % server)
            else:
                failed.append('failed to start %s oblogproxy' % server)

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
        plugin_context.return_true(need_bootstrap=False)
