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
import re
import sys
import time
import random
import base64
import tempfile
from copy import deepcopy

from Crypto import Random
from Crypto.Cipher import AES

from _errno import WC_OBAGENT_SERVER_NAME_ERROR
from ssh import SshClient, SshConfig
from tool import YamlLoader, FileUtil

stdio = None
OBAGNET_CONFIG_MAP = {
    "monitor_password": "{ocp_agent_monitor_password}",
    "sql_port": "{mysql_port}",
    "rpc_port": "{rpc_port}",
    "cluster_name": "{appname}",
    "cluster_id": "{cluster_id}",
    "zone_name": "{zone}",
    "ob_log_path": "{home_path}/store",
    "ob_data_path": "{home_path}/store",
    "ob_install_path": "{home_path}",
    "observer_log_path": "{home_path}/log",
}

if sys.version_info.major == 2:

    def generate_key(key):
        genKey = [chr(0)] * 16
        for i in range(min(16, len(key))):
            genKey[i] = key[i]
        i = 16
        while i < len(key):
            j = 0
            while j < 16 and i < len(key):
                genKey[j] = chr(ord(genKey[j]) ^ ord(key[i]))
                j, i = j + 1, i + 1
        return "".join(genKey)


    class AESCipher:
        bs = AES.block_size

        def __init__(self, key):
            self.key = generate_key(key)

        def encrypt(self, message):
            message = self._pad(message)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return base64.b64encode(iv + cipher.encrypt(message)).decode('utf-8')

        def _pad(self, s):
            return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

else:
    def generate_key(key):
        genKey = [0] * 16
        for i in range(min(16, len(key))):
            genKey[i] = key[i]
        i = 16
        while i < len(key):
            j = 0
            while j < 16 and i < len(key):
                genKey[j] = genKey[j] ^ key[i]
                j, i = j + 1, i + 1
        genKey = [chr(k) for k in genKey]
        return bytes("".join(genKey), encoding="utf-8")


    class AESCipher:
        bs = AES.block_size

        def __init__(self, key):
            self.key = generate_key(key)

        def encrypt(self, message):
            message = self._pad(message)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return str(base64.b64encode(iv + cipher.encrypt(bytes(message, encoding='utf-8'))), encoding="utf-8")

        def _pad(self, s):
            return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)


def encrypt(key, data):
    key = base64.b64decode(key)
    cipher = AESCipher(key)
    return cipher.encrypt(data)


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
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


def generate_aes_b64_key():
    n = random.randint(1, 3) * 8
    key = []
    c = 0
    while c < n:
        key += chr(random.randint(33, 127))
        c += 1
    key = ''.join(key)
    return base64.b64encode(key.encode('utf-8'))


def get_missing_required_parameters(parameters):
    results = []
    for key in OBAGNET_CONFIG_MAP:
        if parameters.get(key) is None:
            results.append(key)
    return results


def prepare_parameters(cluster_config):
    env = {}
    depend_info = {}
    ob_servers_config = {}
    depends_keys = ["ocp_agent_monitor_password", "appname", "cluster_id"]
    for comp in ["oceanbase", "oceanbase-ce"]:
        if comp in cluster_config.depends:
            observer_globals = cluster_config.get_depend_config(comp)
            for key in depends_keys:
                value = observer_globals.get(key)
                if value is not None:
                    depend_info[key] = value
            ob_servers = cluster_config.get_depend_servers(comp)
            for server in ob_servers:
                ob_servers_config[server] = cluster_config.get_depend_config(comp, server)

    for server in cluster_config.servers:
        server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        user_server_config = deepcopy(cluster_config.get_server_conf(server))
        if 'monagent_host_ip' not in user_server_config:
            server_config['monagent_host_ip'] = server.ip
        missed_keys = get_missing_required_parameters(user_server_config)
        if missed_keys and server in ob_servers_config:
            for key in depend_info:
                ob_servers_config[server][key] = depend_info[key]
            for key in missed_keys:
                server_config[key] = OBAGNET_CONFIG_MAP[key].format(server_ip=server.ip, **ob_servers_config[server])
        env[server] = server_config
    return env


def start(plugin_context, is_reinstall=False, *args, **kwargs):
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    options = plugin_context.options
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    pid_path = {}
    yaml = YamlLoader(stdio)
    start_env = plugin_context.get_variable('start_env')

    if not start_env:
        start_env = prepare_parameters(cluster_config)

    repository_dir = None
    for repository in plugin_context.repositories:
        if repository.name == cluster_config.name:
            repository_dir = repository.repository_dir
            break
    with FileUtil.open(os.path.join(repository_dir, 'conf/obd_agent_mapper.yaml')) as f:
        config_mapper = yaml.load(f).get('config_mapper', {})
    stdio.start_loading('Start obagent')

    for comp in ["oceanbase", "oceanbase-ce"]:
        if cluster_config.get_depend_config(comp) and plugin_context.get_return('start', comp).get_return('need_bootstrap'):
            error_servers_list = []
            for server in cluster_config.servers:
                if not cluster_config.get_depend_config(comp, server):
                    error_servers_list.append(server)
            if error_servers_list:
                error_servers_msg = ', '.join(map(lambda x: str(x), error_servers_list))
                stdio.warn(WC_OBAGENT_SERVER_NAME_ERROR.format(servers=error_servers_msg))

    targets = []
    for server in cluster_config.servers:
        client = clients[server]
        server_config = start_env[server]
        home_path = server_config['home_path']
        pid_path[server] = '%s/run/ob_agentd.pid' % home_path
        mgragent_http_port = int(server_config['mgragent_http_port'])
        targets.append('{}:{}'.format(server.ip, mgragent_http_port))
        remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            continue

        home_path = server_config['home_path']
        use_parameter = True
        config_flag = os.path.join(home_path, '.configured')
        if getattr(options, 'without_parameter', False) and client.execute_command('ls %s' % config_flag):
            use_parameter = False

        if is_reinstall:
            use_parameter = True

        if use_parameter:
            # todo: set agent secret key
            mgr_conf = os.path.join(home_path, 'conf/mgragent.yaml')
            mon_conf = os.path.join(home_path, 'conf/monagent.yaml')
            agent_conf = os.path.join(home_path, 'conf/agentctl.yaml')
            for conf in [mgr_conf, mon_conf, agent_conf]:
                ret = client.execute_command('cat {}'.format(conf))
                if ret:
                    content = ret.stdout
                    content = re.sub(r"cryptoMethod:\s+aes", "cryptoMethod: plain", content)
                    client.write_file(content, conf)
                    client.execute_command('chmod 755 {}'.format(conf))
            for key in server_config:
                if server_config[key] is None:
                    server_config[key] = ''
                if isinstance(server_config[key], bool):
                    server_config[key] = str(server_config[key]).lower()

            cmds = []
            for key, value in server_config.items():
                if key in config_mapper:
                    cmds.append("%s=%s" % (config_mapper[key], value))
            cmd = 'cd %s;%s/bin/ob_agentctl config -u %s && touch %s' % (home_path, home_path, ','.join(cmds), config_flag)
            res = client.execute_command(cmd)
            if not res:
                stdio.error('failed to set config to {} obagent.'.format(server))
                return plugin_context.return_false()

        if not client.execute_command('cd %s;%s/bin/ob_agentctl start' % (home_path, home_path)):
            stdio.error('failed to start {} obagent.'.format(server))
            return plugin_context.return_false()

    stdio.stop_loading('succeed')
    stdio.start_loading('obagent program health check')
    time.sleep(1)
    failed = []
    servers = cluster_config.servers
    count = 20
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            client = clients[server]
            server_config = start_env[server]
            home_path = server_config['home_path']
            stdio.verbose('%s program health check' % server)
            pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
            if pid:
                mgr_pid = client.execute_command("cat %s" % os.path.join(home_path, 'run/ob_mgragent.pid')).stdout.strip()
                if mgr_pid and confirm_port(client, mgr_pid, int(server_config["mgragent_http_port"])):
                    stdio.verbose('%s obagent[pid: %s] started', server, pid)
                elif count:
                    tmp_servers.append(server)
                else:
                    failed.append('failed to start %s obagent' % server)
            else:
                failed.append('failed to start %s obagent' % server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        plugin_context.return_false()
    else:
        global_config = cluster_config.get_global_conf()
        target_sync_configs = global_config.get('target_sync_configs', [])
        stdio.verbose('start to sync target config')
        data = [{'targets': targets}]
        default_ssh_config = None
        for client in clients.values():
            default_ssh_config = client.config
            break
        for target_sync_config in target_sync_configs:
            host = None
            target_dir = None
            try:
                host = target_sync_config.get('host')
                target_dir = target_sync_config.get('target_dir')
                if not host or not target_dir:
                    continue
                ssh_config_keys = ['username', 'password', 'port', 'key_file', 'timeout']
                auth_keys = ['username', 'password', 'key_file']
                for key in auth_keys:
                    if key in target_sync_config:
                        config = SshConfig(host)
                        break
                else:
                    config = deepcopy(default_ssh_config)
                for key in ssh_config_keys:
                    if key in target_sync_config:
                        setattr(config, key, target_sync_config[key])
                with tempfile.NamedTemporaryFile(suffix='.yaml') as f:
                    yaml.dump(data, f)
                    f.flush()
                    file_name = '{}.yaml'.format(deploy_name or hash(cluster_config))
                    file_path = os.path.join(target_dir, file_name)
                    remote_client = SshClient(config)
                    remote_client.connect()
                    remote_client.put_file(f.name, file_path)
            except:
                stdio.warn('failed to sync target to {}:{}'.format(host, target_dir))
                stdio.exception('')
        stdio.stop_loading('succeed')
        plugin_context.return_true(need_bootstrap=False)


