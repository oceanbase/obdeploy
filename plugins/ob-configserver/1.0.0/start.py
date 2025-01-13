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

from tool import YamlLoader, NetUtil


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
    if not server_config['storage'].get('connection_url'):
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
        ip = NetUtil.get_host_ip() if client.is_localhost() else server.ip

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
            return
    stdio.stop_loading('succeed')

    plugin_context.return_true()
