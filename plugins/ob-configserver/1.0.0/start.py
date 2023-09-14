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

import os
import time

from _errno import EC_OBC_PROGRAM_START_ERROR
from const import CONST_OBD_HOME
from tool import YamlLoader


def check_home_path_pid(home_path, client):
    """
    Check the process in the current directory is running
    """
    pid_path = "%s/run/ob-configserver.pid" % home_path
    pid = client.execute_command("cat %s" % pid_path).stdout.strip()
    if not pid or not client.execute_command('ls /proc/%s' % pid):
        return False
    return True


def get_config_dict(home_path, server_config, ip):
    """
    Init config dict
    """

    # ip port
    if server_config.get('vip_address'):
        vip_address = server_config.get('vip_address')
        vip_port = int(server_config.get('vip_port'))
    else:
        vip_address = ip
        vip_port = int(server_config['listen_port'])

    # connect_url
    if not server_config['storage']['connection_url']:
        connection_url = os.path.join(home_path, '.data.db?cache=shared&_fk=1')
    else:
        connection_url = server_config['storage']['connection_url']

    config_dict = {
        "log": {
            "level": server_config['log_level'],
            "filename": os.path.join(home_path, "log/ob-configserver.log"),
            "maxsize": int(server_config['log_maxsize']),
            "maxage": int(server_config['log_maxage']),
            "maxbackups": int(server_config['log_maxbackups']),
            "localtime": server_config['log_localtime'],
            "compress": server_config['log_compress'],
        },
        "server": {
            "address": "%s:%s" % (server_config['server_ip'], server_config['listen_port']),
            "run_dir": "run",
        },
        "vip": {
            "address": vip_address,
            "port": vip_port
        },
        "storage": {
            "database_type": server_config['storage']['database_type'],
            "connection_url": connection_url
        }

    }

    return config_dict


def start(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    stdio.start_loading('Start ob-configserver')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        ip = server.ip

        if check_home_path_pid(home_path, client):
            stdio.verbose('%s is runnning, skip' % server)
            continue

        config_dict = get_config_dict(home_path, server_config, ip)
        yaml = YamlLoader()
        file_path = os.path.join(home_path, 'conf/ob-configserver.yaml')
        if not client.write_file(yaml.dumps(config_dict), file_path):
            stdio.error('{ip}: failed to write ob-configserver config.'.format(ip=ip))
            stdio.stop_loading('failed')
            plugin_context.return_false()
            return

        cmd = "nohup {0}/bin/ob-configserver -c {0}/conf/ob-configserver.yaml >> {0}/log/ob-configserver.log 2>&1 & echo $! > {0}/run/ob-configserver.pid".format(home_path)
        if not client.execute_command(cmd):
            stdio.error('Failed to start ob-configserver')
            stdio.stop_loading('failed')
            plugin_context.return_false()
            return
    stdio.stop_loading('succeed')


    stdio.start_loading("ob-configserver program health check")
    time.sleep(1)
    failed = []
    servers = cluster_config.servers
    count = 20
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            if server in tmp_servers:
                continue
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config["home_path"]
            pid_path = '%s/run/ob-configserver.pid' % home_path
            stdio.verbose('%s program health check' % server)
            pid = client.execute_command("cat %s" % pid_path).stdout.strip()
            if pid:
                if client.execute_command('ls /proc/%s' % pid):
                    stdio.verbose('%s ob-configserver[pid: %s] started', server, pid)
                elif count:
                    tmp_servers.append(server)
                else:
                    failed.append(server)
            else:
                failed.append(server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)
    if failed:
        stdio.stop_loading('fail')
        for server in failed:
            stdio.error(EC_OBC_PROGRAM_START_ERROR.format(server=server))
        plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
