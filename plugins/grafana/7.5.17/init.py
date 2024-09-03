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
from tool import OrderedDict
from _errno import EC_CONFIG_CONFLICT_DIR, EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage, EC_COMPONENT_DIR_NOT_EMPTY

stdio = None
force = False
global_ret = True

def critical(*arg, **kwargs):
    global global_ret
    global_ret = False
    stdio.error(*arg, **kwargs)


def init(plugin_context, *args, **kwargs):
    global stdio, force
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    servers_dirs = {}
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    stdio.start_loading('Initializes grafana work home')

    path_list = ['data_dir','logs_dir', 'plugins_dir', 'provisioning_dir']
    all_path_list = ['home_path'] + path_list
    for server in cluster_config.servers:
        ip = server.ip
        if ip not in servers_dirs:
            servers_dirs[ip] = {}
        dirs = servers_dirs[ip]
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']

        for key in all_path_list:
            if server_config.get(key):
                path = server_config[key]
                if path in dirs:
                    critical(EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']))
                    continue
                dirs[path] = {
                    'server': server,
                    'key': key,
                }

        stdio.verbose('%s init grafana work home', server)
        need_clean = force
        if clean and not force:
            if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True
        
        bin_path = '%s/bin/grafana-server' % home_path
        grafana_pid_path = '%s/run/grafana.pid' % home_path
        ini_path = '%s/conf/obd-grafana.ini' % home_path
        pid_cmd = '%s --homepath=%s --config=%s --pidfile=%s' % (bin_path, home_path, ini_path, grafana_pid_path)
        if need_clean:
            clean_ret = True
            client.execute_command(
                "pkill -9 -u `whoami` -f '%s'" % (pid_cmd))
            for key in all_path_list:
                if server_config.get(key):
                    ret = client.execute_command('rm -fr %s/*' % server_config[key], timeout=-1)
                    if not ret:
                        clean_ret = False
                        critical(EC_FAIL_TO_INIT_PATH.format(server=server, key=server_config[key], msg=ret.stderr))
            if not clean_ret:
                continue
        
        ret = client.execute_command('bash -c "mkdir -p %s/{run,conf}"' % home_path)
        if ret:
            link_path_map = OrderedDict({
                'data_dir': 'data',
                'logs_dir': 'data/log',
                'plugins_dir': 'data/plugins',
                'provisioning_dir': 'conf/provisioning'
            })
            mkdir_ret = True
            for k in path_list:
                link_path = os.path.join(home_path, link_path_map[k]) 
                target_path = server_config.get(k, link_path)
                if client.execute_command('mkdir -p %s' % target_path):
                    ret = client.execute_command('ls %s' % target_path)
                    if not ret or ret.stdout.strip():
                        critical(EC_FAIL_TO_INIT_PATH.format(server=server, key=k, msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=target_path)))
                        critical(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                        mkdir_ret = False
                        continue
                    client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (target_path, link_path, target_path, link_path))
            if not mkdir_ret:
                continue

        dashboard_template_path = os.path.join(home_path, 'conf/provisioning/dashboards/templates')
        if client.execute_command('bash -c "mkdir -p %s"' % dashboard_template_path):
            file_name = 'oceanbase-metrics_rev1.json'
            ob_dashboard = os.path.join(os.path.split(__file__)[0], file_name)
            client.put_file(ob_dashboard, os.path.join(dashboard_template_path, file_name))
        else:
            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='conf/provisioning/dashboards/templates', msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=dashboard_template_path)))
            continue
        
        link_path = os.path.join(home_path, 'log')
        target_path = os.path.join(home_path, 'data/log')
        client.execute_command("ln -s %s %s" % (target_path, link_path))

    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')