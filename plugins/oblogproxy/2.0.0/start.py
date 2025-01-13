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

import json
import os

from tool import FileUtil
from tool import confirm_port


def is_started(client, port, remote_pid_path, home_path, stdio):
    ret = client.execute_command("ps -aux | grep '{0}/bin/logproxy -f {0}/conf/conf.json' | grep -v grep | awk '{print $2}' ".format(home_path))
    if not ret:
        return False
    pids = ret.stdout.strip()
    if not pids:
        return False
    pids = pids.split('\n')
    for pid in pids:
        if confirm_port(client, pid, port):
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
            stdio.stop_loading('fail')
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
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
