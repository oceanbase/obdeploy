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
import sys
import time
import socket
import tempfile
from io import BytesIO

from tool import YamlLoader, FileUtil
from ruamel.yaml.comments import CommentedMap

if sys.version_info.major == 2:
    from ConfigParser import ConfigParser as _ConfigParser
    class ConfigParser(_ConfigParser):
        def read_file(self, fp, filename=None):
            return self.readfp(fp, filename)
else:
    from configparser import ConfigParser

stdio = None
_grafana_conf_from_prometheus = None
local_ip = None


def get_loacl_ip():
    global local_ip
    if local_ip is None:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    return local_ip


def get_server_ip(server):
    return get_loacl_ip() if server.ip == '127.0.0.1' else server.ip 


def get_port_socket_inode(client, port,stdio):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    return res.stdout.strip().split('\n')


def confirm_port(client, pid, port, stdio):
    socket_inodes = get_port_socket_inode(client, port, stdio)
    if not socket_inodes:
        return False
    ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False


def start(plugin_context, local_home_path, repository_dir, need_bootstrap=False, repository_dir_map=None, *args, **kwargs):  
   
    def spear_dict(di_, con_s='.'):
        def prefix_dict(di_, prefix_s=''):
            return {prefix_s + k: v for k, v in di_.items()} 

        ret = {}
        for k, v in di_.items():
            if type(v) is CommentedMap:
                v = spear_dict(v)
                for k_, v_ in v.items():
                    ret.update({con_s.join([k, k_]): v_})
                    ret.update(prefix_dict(v, prefix_s=k + con_s))
            else:
                ret[k] = v
        return ret

    def generate_ini():
        ini_dict = {}
        if 'customize_config' in server_config:
            ini_dict.update(spear_dict(server_config['customize_config']))
        return ini_dict

    def check_parameter(ini_dict):
        fail_message = []
        for key in ini_dict:
            if key in invalid_key_map:
                fail_message.append('invalid customize parameter {}, please set configuration {} instead.'.format(key, invalid_key_map[key]))
        return fail_message

    def generate_ini_file(home_path, ini_dict):
        remote_ini_path = os.path.join(home_path, 'conf/obd-grafana.ini')
        f = BytesIO()
        config_parser = ConfigParser()
        config_parser.read_file(f)
        section_list = []
        for k in ini_dict:
            section = k.rsplit(".",1)[0]
            key = k.rsplit(".",1)[1]
            if section not in section_list:
                config_parser.add_section(section)
                section_list.append(section)
            config_parser.set(section, key, str(ini_dict[k]))
        try:
            with tempfile.NamedTemporaryFile('w+', suffix=".ini") as tf:
                config_parser.write(tf)
                tf.flush()
                return client.put_file(tf.name, remote_ini_path) 
        except Exception as e:
            stdio.exception(e)
            return False

    
    def generate_datasource_yaml(prometheus_server, prometheus_server_config):
        datasource_path = os.path.join(home_path, 'conf/provisioning/datasources/sample.yaml')
        datasources_conf_content = CommentedMap()
        datasources_conf_content['apiVersion'] = 1
        datasource_conf = []
        if prometheus_server_config:
            ob_prome_conf = {'name': 'OB-Prometheus', 'isDefault': 'true', 'type': 'prometheus', 'access': 'proxy',  'editable': 'true'}
            ip = get_server_ip(prometheus_servers[0])
            port = prometheus_server_config['port']
            ssl = False
            if prometheus_server_config.get('web_config', {}).get('tls_server_config'):
                if prometheus_server_config['web_config']['tls_server_config'] and prometheus_server_config['web_config']['tls_server_config'].get('cert_file'):
                    ssl = True
            url = '%s://%s:%s' %('https' if ssl else 'http', ip, port)
            ob_prome_conf.update({'url': url})
            if prometheus_server_config.get('basic_auth_users'):
                for key, value in prometheus_server_config['basic_auth_users'].items():
                    stdio.verbose('prometheus_server_config: %s ' % prometheus_server_config['basic_auth_users'])
                    ob_prome_conf.update({'basicAuth': 'true'})
                    ob_prome_conf.update({'basicAuthUser': key })
                    ob_prome_conf.update({'secureJsonData': {'basicAuthPassword' : value}})
                    break
            datasource_conf.append(ob_prome_conf)

        if server_config.get('datasources'):
            for datasource in server_config['datasources']:
                if datasource.get('name'):
                    if datasource['name'] == 'OB-Prometheus':
                        stdio.warn('%s server grafana datasource\'s name can not be "OB-Prometheus", you should use another one' % server)
                        return False
                else:
                    stdio.warn('datasource does not have "name" proprity')
                    return False  
                datasource_conf.append(datasource)
        datasources_conf_content.update({'datasources': datasource_conf})
        try:
            config_content = yaml.dumps(datasources_conf_content).strip()
            if client.write_file(config_content, datasource_path):
                return True
            stdio.error('failed to write config file {}'.format(datasource_path))
            return False
        except Exception as e:

            stdio.exception(e)
            return False
        
    def generate_provider_yaml():
        provider_path = os.path.join(home_path, 'conf/provisioning/dashboards/sample.yaml')
        template_path = os.path.join(home_path, 'conf/provisioning/dashboards/templates')
        provider_conf_content = CommentedMap()
        provider_conf_content['apiVersion'] = 1
        ob_metrics_conf = {'name': 'OceanBase Metrics', 'type': 'file', 'allowUiUpdates': 'true',  'options': {'path': template_path}}
        provider_conf = []
        if 'prometheus' in cluster_config.depends:
            provider_conf.append(ob_metrics_conf)
        if server_config.get('providers'):
            for provider in server_config['providers']:
                if provider.get('name'):
                    if provider['name'] == 'Oceanbase Metrics':
                        stdio.warn('%s server grafana provider\'s name can not be "Oceanbase Metrics", you should use another one' % server)
                        return False
                else:
                    stdio.warn('provier does not have "name" proprity')
                    return False  
                provider_conf.append(provider)
        
        provider_conf_content.update({'providers': provider_conf})
        try:
            config_content = yaml.dumps(provider_conf_content).strip()
            if client.write_file(config_content, provider_path):
                return True
            stdio.error('failed to write config file {}'.format(provider_path))
            return False
        except Exception as e:
            stdio.exception(e)
            return False

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global _grafana_conf_from_prometheus
    _grafana_conf_from_prometheus = None
    need_bootstrap = True
    yaml = YamlLoader(stdio=stdio)
    invalid_key_map = {
        'paths.data': 'data_dir',
        'paths.logs': 'log_dir',
        'paths.plugins': 'plugins_dir',
        'paths.provisioning': 'provisioning_dir',
        'paths.temp_data_lifetime': 'temp_data_lifetime',
        'server.domain': 'domain',
        'server.http_port': 'port',
        'security.admin_password': 'login_password',
        'log.file.max_days': 'log_max_days',
    }
    stdio.start_loading('Start grafana')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']


    servers_pid = {}
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']

        ini_dict = generate_ini()
        fail_message = check_parameter(ini_dict)
        if fail_message:
            for msg in fail_message:
                stdio.warn('%s: %s' %(server, msg))
            stdio.stop_loading('fail')
            return False

        prometheus_server_config = {}
        prometheus_server = []
        if 'prometheus' in cluster_config.depends:
            prometheus_servers = cluster_config.get_depend_servers('prometheus')
            prometheus_server.append(prometheus_servers[0])
            prometheus_server_config = cluster_config.get_depend_config('prometheus', prometheus_servers[0])
            
        key_map = {'port': 'server.http_port',
                    'domain': 'server.domain',
                    'log_max_days': 'log.file.max_days',
                    'temp_data_lifetime': 'paths.temp_data_lifetime'}
        for key in key_map:
            if key in server_config:
                ini_dict[key_map[key]] = server_config[key]

        stdio.verbose('%s generate obd-grafana ini file' % server)
        if not generate_ini_file(home_path, ini_dict):
            stdio.verbose('%s obd-grafana ini file generate failed' % server)
            stdio.stop_loading('fail')   
            return False
        stdio.verbose('%s generate datasources yaml' % server)
        if not generate_datasource_yaml(prometheus_server, prometheus_server_config):
            stdio.verbose('%s grafana datasources yaml generate failed' % server)
            stdio.stop_loading('fail')
            return False
        stdio.verbose('%s generate providers yaml' % server)
        if not generate_provider_yaml():
            stdio.verbose('%s grafana providers yaml generate failed' % server)
            stdio.stop_loading('fail')
            return False

        ini_path = os.path.join(server_config["home_path"], 'conf/obd-grafana.ini')
        grafana_pid_path = os.path.join(server_config["home_path"], 'run/grafana.pid')
        bin_path = os.path.join(server_config["home_path"], 'bin/grafana-server')
        log_path = os.path.join(server_config["home_path"], 'data/log/grafana-console.log')
       
        pid_cmd = '%s --homepath=%s --config=%s --pidfile=%s' % (bin_path, home_path, ini_path, grafana_pid_path)
        ret = client.execute_command('''ps -aux | grep -e '%s$' | grep -v grep | awk '{print $2}' ''' % pid_cmd)
        if ret:
            for pid in ret.stdout.strip().split('\n'):
                if pid and client.execute_command('ls /proc/%s/fd' % pid):
                    client.execute_command('kill -9 {}'.format(pid))
        cmd = '%s --homepath=%s --config=%s --pidfile=%s > %s 2>&1 &' % (bin_path, home_path, ini_path, grafana_pid_path, log_path)
       
        ret = client.execute_command("cd %s; bash -c '%s'" % (home_path, cmd))
        if not ret:
            stdio.stop_loading('fail')
            stdio.error('failed to start %s grafana: %s' % (server, ret.stderr))
            return plugin_context.return_false()
        ret = client.execute_command('''ps -aux | grep -e '%s$' | grep -v grep | awk '{print $2}' ''' % pid_cmd)
        if ret:
            servers_pid[server] = ret.stdout.strip().split('\n')
    stdio.stop_loading('succeed')

    time.sleep(1)
    stdio.start_loading('grafana program health check')
    failed = []
    servers = cluster_config.servers
    count = 20
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            home_path = server_config['home_path']
            stdio.verbose('%s program health check' % server)
            stdio.verbose('servers_pid: %s ' % servers_pid)
            if servers_pid.get(server):
                for pid in servers_pid[server]:
                    confirm = confirm_port(client, pid, int(server_config["port"]), stdio)
                    if confirm:
                        grafana_pid_path = os.path.join(home_path, 'run/grafana.pid')
                        ret = client.execute_command('cat %s' % grafana_pid_path)
                        if ret.stdout.strip('\n') == pid :
                            stdio.verbose('%s grafana[pid: %s] started', server, pid)
                        else:
                            tmp_servers.append(server)
                        break
                    stdio.verbose('failed to start %s grafana, remaining retries: %d' % (server, count))
                    if count:
                        tmp_servers.append(server)
                    else:
                        failed.append('failed to start %s grafana' % server)   
            else:
                failed.append('failed to start %s grafana' % server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)
    
    if failed:
        stdio.stop_loading('failed')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true(need_bootstrap=need_bootstrap)
