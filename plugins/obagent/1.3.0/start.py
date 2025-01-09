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

from _errno import WC_OBAGENT_SERVER_NAME_ERROR
from tool import YamlLoader, FileUtil

stdio = None


def start(plugin_context, is_reinstall=False, *args, **kwargs):
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    options = plugin_context.options
    stdio = plugin_context.stdio
    pid_path = {}
    yaml = YamlLoader(stdio)
    start_env = plugin_context.get_variable('start_env')

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
    plugin_context.set_variable('targets', targets)
    plugin_context.set_variable('pid_path', pid_path)
    plugin_context.return_true(need_bootstrap=False)


