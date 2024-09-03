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
import time
import requests
from copy import deepcopy
from urllib.parse import urlparse

from _errno import EC_OBSERVER_FAIL_TO_START, EC_OBSERVER_FAIL_TO_START_WITH_ERR, EC_OBSERVER_FAILED_TO_REGISTER, EC_OBSERVER_FAILED_TO_REGISTER_WITH_DETAILS, EC_OBSERVER_FAIL_TO_START_OCS

from collections import OrderedDict

from tool import NetUtil, ConfigUtil


def get_ob_configserver_cfg_url(obconfig_url, appname, stdio):
    parsed_url = urlparse(obconfig_url)
    host = parsed_url.netloc
    stdio.verbose('obconfig_url host: %s' % host)
    url = '%s://%s/debug/pprof/cmdline' % (parsed_url.scheme, host)
    try:
        response = requests.get(url, allow_redirects=False)
        if response.status_code != 200:
            stdio.verbose('request %s status_code: %s' % (url, str(response.status_code)))
            return None
    except Exception:
        stdio.verbose('Configserver url check failed: request %s failed' % url)
        return None

    if obconfig_url[-1] == '?':
        link_char = ''
    elif obconfig_url.find('?') == -1:
        link_char = '?'
    else:
        link_char = '&'
    cfg_url = '%s%sAction=ObRootServiceInfo&ObCluster=%s' % (obconfig_url, link_char, appname)
    return cfg_url


def config_url(ocp_config_server, appname, cid):
    if ocp_config_server[-1] == '?':
        link_char = ''
    elif ocp_config_server.find('?') == -1:
        link_char = '?'
    else:
        link_char = '&'
    cfg_url = '%s%sAction=ObRootServiceInfo&ObCluster=%s' % (ocp_config_server, link_char, appname)
    proxy_cfg_url = '%s%sAction=GetObProxyConfig&ObRegionGroup=%s' % (ocp_config_server, link_char, appname)
    # Command that clears the URL content for the cluster
    cleanup_config_url_content = '%s%sAction=DeleteObRootServiceInfoByClusterName&ClusterName=%s' % (ocp_config_server, link_char, appname)
    # Command that register the cluster information to the Config URL
    register_to_config_url = '%s%sAction=ObRootServiceRegister&ObCluster=%s&ObClusterId=%s' % (ocp_config_server, link_char, appname, cid)
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


class EnvVariables(object):

    def __init__(self, environments, client):
        self.environments = environments
        self.client = client
        self.env_done = {}

    def __enter__(self):
        for env_key, env_value in self.environments.items():
            self.env_done[env_key] = self.client.get_env(env_key)
            self.client.add_env(env_key, env_value, True)

    def __exit__(self, *args, **kwargs):
        for env_key, env_value in self.env_done.items():
            if env_value is not None:
                self.client.add_env(env_key, env_value, True)
            else:
                self.client.del_env(env_key)


def construct_opts(server_config, param_list, rs_list_opt, cfg_url, cmd, need_bootstrap):
    not_opt_str = OrderedDict({
                'mysql_port': '-p',
                'rpc_port': '-P',
                'zone': '-z',
                'nodaemon': '-N',
                'appname': '-n',
                'cluster_id': '-c',
                'data_dir': '-d',
                'devname': '-i',
                'syslog_level': '-l',
                'ipv6': '-6',
                'mode': '-m',
                'scn': '-f',
                'local_ip': '-I'
            })
    not_cmd_opt = [
        'home_path', 'obconfig_url', 'root_password', 'proxyro_password', 'scenario',
        'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir', '$_zone_idc', 'production_mode',
        'ocp_monitor_tenant', 'ocp_monitor_username', 'ocp_monitor_password', 'ocp_monitor_db',
        'ocp_meta_tenant', 'ocp_meta_username', 'ocp_meta_password', 'ocp_meta_db', 'ocp_agent_monitor_password', 'ocp_root_password', 'obshell_port'
    ]
    get_value = lambda key: "'%s'" % server_config[key] if isinstance(server_config[key], str) else server_config[key]

    opt_str = []
    for key in param_list:
        if key not in not_cmd_opt and key not in not_opt_str and not key.startswith('ocp_meta_tenant_'):
            value = get_value(key)
            opt_str.append('%s=%s' % (key, value))
    if need_bootstrap:
        if cfg_url:
            opt_str.append('obconfig_url=\'%s\'' % cfg_url)
        else:
            cmd.append(rs_list_opt)

    param_list['mysql_port'] = server_config['mysql_port']
    for key in not_opt_str:
        if key in param_list:
            value = get_value(key)
            cmd.append('%s %s' % (not_opt_str[key], value))
    if len(opt_str) > 0:
        cmd.append('-o %s' % ','.join(opt_str))

def start(plugin_context, new_cluster_config=None, start_obshell=True, *args, **kwargs):
    cluster_config = new_cluster_config if new_cluster_config else plugin_context.cluster_config
    options = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    clusters_cmd = {}
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
        cfg_url = get_ob_configserver_cfg_url(obconfig_url, appname, stdio)
        if not cfg_url:
            try:
                cfg_url = init_config_server(obconfig_url, appname, cluster_id, getattr(options, 'force_delete', False),
                                             stdio)
                if not cfg_url:
                    stdio.warn(EC_OBSERVER_FAILED_TO_REGISTER_WITH_DETAILS.format(appname, obconfig_url))
            except:
                stdio.warn(EC_OBSERVER_FAILED_TO_REGISTER.format())
    elif 'ob-configserver' in cluster_config.depends and appname:
        obc_cluster_config = cluster_config.get_depend_config('ob-configserver')
        vip_address = obc_cluster_config.get('vip_address')
        if vip_address:
            obc_ip = vip_address
            obc_port = obc_cluster_config.get('vip_port')
        else:
            server = cluster_config.get_depend_servers('ob-configserver')[0]
            client = clients[server]
            obc_ip = NetUtil.get_host_ip() if client.is_localhost() else server.ip
            obc_port = obc_cluster_config.get('listen_port')
        cfg_url = "http://{0}:{1}/services?Action=ObRootServiceInfo&ObCluster={2}".format(obc_ip, obc_port, appname)

    if cluster_config.added_servers:
        scale_out = True
        need_bootstrap = False
    else:
        scale_out = False
        need_bootstrap = True
    stdio.start_loading('Start observer')
    for server in cluster_config.original_servers:
        config = cluster_config.get_server_conf(server)
        zone = config['zone']
        if zone not in root_servers:
            root_servers[zone] = '%s:%s:%s' % (server.ip, config['rpc_port'], config['mysql_port'])
    rs_list_opt  = '-r \'%s\'' % ';'.join([root_servers[zone] for zone in root_servers])
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']

        param_config = {}
        if new_cluster_config:
            old_config = plugin_context.cluster_config.get_server_conf_with_default(server)
            new_config = new_cluster_config.get_server_conf_with_default(server)
            for key in new_config:
                param_value = new_config[key]
                if key not in old_config or old_config[key] != param_value:
                    param_config[key] = param_value
        else:
            param_config = server_config

        if not server_config.get('data_dir'):
            server_config['data_dir'] = '%s/store' % home_path
            
        if not server_config.get('local_ip') and not server_config.get('devname'):
            server_config['local_ip'] = server.ip

        if client.execute_command('ls %s/clog/tenant_1/' % server_config['data_dir']).stdout.strip():
            need_bootstrap = False

        remote_pid_path = '%s/run/observer.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                continue

        stdio.verbose('%s start command construction' % server)
        if getattr(options, 'without_parameter', False) and client.execute_command('ls %s/etc/observer.config.bin' % home_path):
            use_parameter = False
        else:
            use_parameter = True
        cmd = []
        if use_parameter:
            construct_opts(server_config, param_config, rs_list_opt, cfg_url, cmd, need_bootstrap)
        else:
            cmd.append('-p %s' % server_config['mysql_port'])

        clusters_cmd[server] = 'cd %s; %s/bin/observer %s' % (home_path, home_path, ' '.join(cmd))
    for server in clusters_cmd:
        environments = deepcopy(cluster_config.get_environments())
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('starting %s observer', server)
        if 'LD_LIBRARY_PATH' not in environments:
            environments['LD_LIBRARY_PATH'] = '%s/lib:' % server_config['home_path']
        with EnvVariables(environments, client):
            ret = client.execute_command(clusters_cmd[server])
        if not ret:
            stdio.stop_loading('fail')
            stdio.error(EC_OBSERVER_FAIL_TO_START_WITH_ERR.format(server=server, stderr=ret.stderr))
            return
    stdio.stop_loading('succeed')

    start_obshell = start_obshell and not need_bootstrap and not scale_out
    stdio.verbose('start_obshell: %s' % start_obshell)
    if start_obshell:
        for server in cluster_config.servers:
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config['home_path']
            obshell_pid_path = '%s/run/obshell.pid' % home_path 
            obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
            if obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid):
                stdio.verbose('%s obshell[pid: %s] started', server, obshell_pid)
            else:
                # start obshell
                server_config = cluster_config.get_server_conf(server)
                password = server_config.get('root_password', '')
                client.add_env('OB_ROOT_PASSWORD', password if client._is_local else ConfigUtil.passwd_format(password))
                cmd = 'cd %s; %s/bin/obshell admin start --ip %s --port %s'%(server_config['home_path'], server_config['home_path'], server.ip, server_config['obshell_port'])
                stdio.verbose('start obshell: %s' % cmd)
                if not client.execute_command(cmd):
                    stdio.error('%s obshell failed', server)
                    return 

    if not scale_out:
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
                failed.append(EC_OBSERVER_FAIL_TO_START.format(server=server))
        if failed:
            stdio.stop_loading('fail')
            for msg in failed:
                stdio.warn(msg)
            return plugin_context.return_false()
        else:
            stdio.stop_loading('succeed')
    
    if start_obshell:
        # check obshell health
        failed = []
        stdio.start_loading('obshell program health check')
        for server in cluster_config.servers:
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config['home_path']
            obshell_pid_path = '%s/run/obshell.pid' % home_path
            obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
            if obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid):
                stdio.verbose('%s obshell[pid: %s] started', server, obshell_pid)
            else:
                failed.append(EC_OBSERVER_FAIL_TO_START_OCS.format(server=server)) # TODO: 增加obshell相关的错误吗
        if failed:
            stdio.stop_loading('fail')
            for msg in failed:
                stdio.warn(msg)
            return plugin_context.return_false()
        else:
            stdio.stop_loading('succeed')
    
    stdio.verbose('need_bootstrap: %s' % need_bootstrap)
    return plugin_context.return_true(need_bootstrap=need_bootstrap)
