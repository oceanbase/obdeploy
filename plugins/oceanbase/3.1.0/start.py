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
import json
import time
import requests
from copy import deepcopy


def config_url(ocp_config_server, appname, cid):
    cfg_url = '%s&Action=ObRootServiceInfo&ObCluster=%s' % (ocp_config_server, appname)
    proxy_cfg_url = '%s&Action=GetObProxyConfig&ObRegionGroup=%s' % (ocp_config_server, appname)
    # Command that clears the URL content for the cluster
    cleanup_config_url_content = '%s&Action=DeleteObRootServiceInfoByClusterName&ClusterName=%s' % (ocp_config_server, appname)
    # Command that register the cluster information to the Config URL
    register_to_config_url = '%s&Action=ObRootServiceRegister&ObCluster=%s&ObClusterId=%s' % (ocp_config_server, appname, cid)
    return cfg_url, cleanup_config_url_content, register_to_config_url


def init_config_server(ocp_config_server, appname, cid, force_delete, stdio):
    def post(url):
        stdio.verbose('post %s' % url)
        response = requests.post(url)
        if response.status_code != 200:
            raise Exception('%s status code %s' % (url, response.status_code))
        return json.loads(response.text)['Code']
    cfg_url, cleanup_config_url_content, register_to_config_url = config_url(ocp_config_server, appname, cid)
    ret = post(register_to_config_url)
    if ret != 200:
        if not force_delete:
            raise Exception('%s may have been registered in %s' % (appname, ocp_config_server))
        ret = post(cleanup_config_url_content)
        if ret != 200 :
            raise Exception('failed to clean up the config url content, return code %s' % ret)
        if post(register_to_config_url) != 200:
            return False
    return cfg_url
        

def start(plugin_context, local_home_path, repository_dir, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    clusters_cmd = {}
    need_bootstrap = True
    bin_path = os.path.join(repository_dir, 'bin/observer')
    root_servers = {}
    global_config = cluster_config.get_global_conf()
    appname = global_config['appname'] if 'appname' in global_config else None
    cluster_id = global_config['cluster_id'] if 'cluster_id' in global_config else None
    obconfig_url = global_config['obconfig_url'] if 'obconfig_url' in global_config else None
    cfg_url = ''
    if obconfig_url:
        if not appname or not cluster_id:
            stdio.error('need appname and cluster_id')
            return 
        try:
            cfg_url = init_config_server(obconfig_url, appname, cluster_id, getattr(options, 'force_delete', False), stdio)
            if not cfg_url:
                stdio.error('failed to register cluster. %s may have been registered in %s.' % (appname, obconfig_url))
                return 
        except:
            stdio.exception('failed to register cluster')
            return

    stdio.start_loading('Start observer')
    for server in cluster_config.servers:
        config = cluster_config.get_server_conf(server)
        zone = config['zone']
        if zone not in root_servers:
            root_servers[zone] = '%s:%s:%s' % (server.ip, config['rpc_port'], config['mysql_port'])
    rs_list_opt  = '-r \'%s\'' % ';'.join([root_servers[zone] for zone in root_servers])

    for server in cluster_config.servers:
        client = clients[server]
        remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
        remote_bin_path = bin_path.replace(local_home_path, remote_home_path)
        server_config = cluster_config.get_server_conf(server)

        req_check = ['home_path', 'cluster_id']
        for key in req_check:
            if key not in server_config:
                stdio.stop_loading('fail')
                stdio.print('%s %s is empty', server, key)
                return plugin_context.return_false()

        home_path = server_config['home_path']
        if 'data_dir' not in server_config:
            server_config['data_dir'] = '%s/store' % home_path

        if client.execute_command('ls %s/clog' % server_config['data_dir']).stdout.strip():
            need_bootstrap = False
        
        remote_pid_path = '%s/run/observer.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                continue

        stdio.verbose('%s start command construction' % server)
        not_opt_str = {
            'zone': '-z',
            'mysql_port': '-p',
            'rpc_port': '-P',
            'nodaemon': '-N',
            'appname': '-n',
            'cluster_id': '-c',
            'data_dir': '-d',
            'devname': '-i',
            'syslog_level': '-l',
            'ipv6': '-6',
            'mode': '-m',
            'scn': '-f'
        }
        get_value = lambda key: "'%s'" % server_config[key] if isinstance(server_config[key], str) else server_config[key]
        opt_str = []
        for key in server_config:
            if key not in ['home_path', 'obconfig_url', 'proxyro_password'] and key not in not_opt_str:
                value = get_value(key)
                opt_str.append('%s=%s' % (key, value))
        cmd = []
        if cfg_url:
            opt_str.append('obconfig_url=\'%s\'' % cfg_url)
        else:
            cmd.append(rs_list_opt)
        cmd.append('-o %s' % ','.join(opt_str))
        for key in not_opt_str:
            if key in server_config:
                value = get_value(key)
                cmd.append('%s %s' % (not_opt_str[key], value))
        clusters_cmd[server] = 'cd %s; %s %s' % (home_path, remote_bin_path, ' '.join(cmd))
        
    for server in clusters_cmd:
        client = clients[server]
        stdio.verbose('starting %s observer', server)
        ret = client.execute_command(clusters_cmd[server])
        if not ret:
            stdio.stop_loading('fail')
            stdio.error('failed to start %s observer: %s' % (server, ret.stderr))
            return
    stdio.stop_loading('succeed')

    stdio.start_loading('observer program health check')
    time.sleep(3)
    failed = []
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        remote_pid_path = '%s/run/observer.pid' % home_path
        stdio.verbose('%s program health check' % server)
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            stdio.verbose('%s observer[pid: %s] started', server, remote_pid)
        else:
            failed.append('failed to start %s observer' % server)
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        return plugin_context.return_true(need_bootstrap=need_bootstrap)
