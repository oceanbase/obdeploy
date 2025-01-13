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
import re
import tempfile
from glob import glob
from copy import deepcopy

from tool import YamlLoader
from _errno import *


stdio = None


def start(plugin_context, *args, **kwargs):
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    options = plugin_context.options
    encrypt = plugin_context.get_variable('encrypt')
    generate_aes_b64_key = plugin_context.get_variable('generate_aes_b64_key')
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
    }

    for repository in plugin_context.repositories:
        if repository.name == cluster_config.name:
            break
    repository_dir = repository.repository_dir

    stdio.start_loading('Start obagent')
    for server in cluster_config.servers:
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

        if getattr(options, 'without_parameter', False) and client.execute_command('ls %s/conf/monagent.yaml' % home_path):
            use_parameter = False
        else:
            use_parameter = True

        if use_parameter:
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
    plugin_context.set_variable('targets', targets)
    plugin_context.set_variable('pid_path', pid_path)
    return plugin_context.return_true()
