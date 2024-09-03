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
from glob import glob
from copy import deepcopy

from Crypto import Random
from Crypto.Cipher import AES

from ssh import SshClient, SshConfig
from tool import YamlLoader
from _errno import *


stdio = None


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
                j, i = j+1, i+1
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
                j, i = j+1, i+1
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


def start(plugin_context, local_home_path, *args, **kwargs):
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    deploy_name = plugin_context.deploy_name
    stdio = plugin_context.stdio
    options = plugin_context.options
    config_files = {}
    pid_path = {}
    targets = []
    yaml = YamlLoader(stdio)
    need_encrypted = []
    config_map =  {
        "monitor_password": "root_password",
        "sql_port": "mysql_port",
        "rpc_port": "rpc_port",
        "cluster_name": "appname",
        "cluster_id": "cluster_id",
        "zone_name": "zone",
        "ob_install_path": "home_path"
    }

    for repository in plugin_context.repositories:
        if repository.name == cluster_config.name:
            break
    repository_dir = repository.repository_dir

    stdio.start_loading('Start obagent')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        targets.append('%s:%s' % (server.ip, server_config["server_port"]))

    for path in glob(os.path.join(repository_dir, 'conf/*/*.yaml')):
        with open(path) as f:
            text = f.read()
            target = set(re.findall('\n((\s+)-\s+\{target\})', text))
            for pt in target:
                text = text.replace(pt[0], ('%s- ' % pt[1]) + ('\n%s- ' % pt[1]).join(targets))

            keys = set(re.findall('\${([\.\w]+)\}', text))
            for key in keys:
                text = text.replace('${%s}' % key, '$\[[%s\]]' % key)
            config_files[path] = text

    for path in glob(os.path.join(repository_dir, 'conf/config_properties/*.yaml')):
        with open(path) as f:
            data = yaml.load(f).get('configs', [])
            for conf in data:
                if conf.get('encrypted'):
                    key = conf.get('value')
                    if key and isinstance(key, dict):
                        key = list(key.keys())[0]
                        need_encrypted.append(key)

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
        server_config = deepcopy(cluster_config.get_server_conf(server))
        default_server_config = cluster_config.get_server_conf_with_default(server)
        obs_config = {}
        home_path = server_config['home_path']
        remote_pid_path = '%s/run/obagent-%s-%s.pid' % (home_path, server.ip, server_config["server_port"])
        pid_path[server] = remote_pid_path
        server_port = int(server_config['server_port'])
        targets.append('{}:{}'.format(server.ip, server_port))
        remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            continue

        for comp in ['oceanbase', 'oceanbase-ce']:
            obs_config = cluster_config.get_depend_config(comp, server)
            if obs_config is not None:
                break

        if obs_config is None:
            obs_config = {}

        for key in config_map:
            k = config_map[key]
            if not server_config.get(key):
                server_config[key] = obs_config.get(k, default_server_config.get(key))

        for key in default_server_config:
            if not server_config.get(key):
                server_config[key] = default_server_config.get(key)

        server_config['host_ip'] = server.ip
        for key in server_config:
            if server_config[key] is None:
                server_config[key] = ''
            if isinstance(server_config[key], bool):
                server_config[key] = str(server_config[key]).lower()
        
        if server_config.get('crypto_method', 'plain').lower() == 'aes':
            secret_key = generate_aes_b64_key()
            crypto_path = server_config.get('crypto_path', 'conf/.config_secret.key')
            crypto_path = os.path.join(home_path, crypto_path)
            client.execute_command('echo "%s" > %s' % (secret_key.decode('utf-8') if isinstance(secret_key, bytes) else secret_key, crypto_path))
            for key in need_encrypted:
                value = server_config.get(key)
                if value:
                    server_config[key] = encrypt(secret_key, value)

        for path in config_files:
            stdio.verbose('format %s' % path)
            with tempfile.NamedTemporaryFile(suffix=".yaml", mode='w') as tf:
                text = config_files[path].format(**server_config)
                text = text.replace('\[[', '{').replace('\]]', '}')
                tf.write(text)
                tf.flush()
                if not client.put_file(tf.name, path.replace(repository_dir, home_path)):
                    stdio.error(EC_OBAGENT_SEND_CONFIG_FAILED.format(server=server))
                    stdio.stop_loading('fail')
                    return 
        
        config = {
            'log': {
                'level': server_config.get('log_level', 'info'),
                'filename': server_config.get('log_path', 'log/monagent.log'),
                'maxsize': int(server_config.get('log_size', 30)),
                'maxage': int(server_config.get('log_expire_day', 7)),
                'maxbackups': int(server_config.get('maxbackups', 10)),
                'localtime': True if server_config.get('log_use_localtime', True) else False,
                'compress': True if server_config.get('log_compress', True) else False
            },
            'server': {
                'address': '0.0.0.0:%d' % server_port,
                'adminAddress': '0.0.0.0:%d' % int(server_config['pprof_port']),
                'runDir': 'run'
            },
            'cryptoMethod': server_config['crypto_method'] if server_config.get('crypto_method').lower() in ['aes', 'plain'] else 'plain',
            'cryptoPath': server_config.get('crypto_path'),
            'modulePath': 'conf/module_config',
            'propertiesPath': 'conf/config_properties'
        }

        with tempfile.NamedTemporaryFile(suffix=".yaml") as tf:
            yaml.dump(config, tf)
            if not client.put_file(tf.name, os.path.join(home_path, 'conf/monagent.yaml')):
                stdio.error(EC_OBAGENT_SEND_CONFIG_FAILED.format(server=server))
                stdio.stop_loading('fail')
                return 
                
        log_path = '%s/log/monagent_stdout.log' % home_path
        client.execute_command('cd %s;nohup %s/bin/monagent -c conf/monagent.yaml >> %s 2>&1 & echo $! > %s' % (home_path, home_path, log_path, remote_pid_path))

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
            server_config = cluster_config.get_server_conf(server)
            stdio.verbose('%s program health check' % server)
            pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
            if pid:
                if confirm_port(client, pid, int(server_config["server_port"])):
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
                    remote_client.connect(stdio=stdio)
                    remote_client.put_file(f.name, file_path, stdio=stdio)
            except:
                stdio.warn('failed to sync target to {}:{}'.format(host, target_dir))
                stdio.exception('')
        stdio.stop_loading('succeed')
        plugin_context.return_true(need_bootstrap=False)
