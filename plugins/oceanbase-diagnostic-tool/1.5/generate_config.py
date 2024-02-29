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
from tool import YamlLoader, FileUtil
from ssh import LocalClient

def generate_config(plugin_context, deploy_config, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key)
        if value is None:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value

    def parse_empty(value,default=''):
        if value is None:
            value = default
        return value

    yaml = YamlLoader()
    options = plugin_context.options
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    global_conf = cluster_config.get_global_conf()
    deploy_name = plugin_context.deploy_name
    user_config = deploy_config.user
    obcluster_config = {}
    obproxy_config = {}
    config_path = os.path.join(os.path.expanduser('~'), ".obdiag/config.yml")

    def get_obdiag_config():
        # obproxy
        obproxy_depend = None
        for comp in ['obproxy', 'obproxy-ce']:
            if comp in deploy_config.components:
                obproxy_depend = comp
                obproxy_servers = deploy_config.components[comp].servers
                obproxy_server = obproxy_servers[0]
                break
        obproxy_nodes = []
        if obproxy_depend:
            obproxy = deploy_config.components[obproxy_depend]
            obproxy_servers = obproxy.servers
            for server in obproxy_servers:
                nodeItem = {}
                nodeItem["ip"] = server.ip
                nodeItem["ssh_port"] = parse_empty(user_config.port)
                nodeItem["ssh_username"] = parse_empty(user_config.username)
                nodeItem["ssh_password"] = parse_empty(user_config.password)
                nodeItem["private_key"] = parse_empty(user_config.key_file)
                server_config = obproxy.get_server_conf(server)
                nodeItem["home_path"] = server_config.get("home_path")
                obproxy_nodes.append(nodeItem)
        obproxy_config["servers"] = {"nodes": obproxy_nodes, "global": {}}

        # observer
        ob_services = cluster_config.servers
        observer_nodes = []
        for server in ob_services:
            nodeItem = {}
            nodeItem["ip"] = server.ip
            nodeItem["ssh_port"] = parse_empty(user_config.port)
            nodeItem["ssh_username"] = parse_empty(user_config.username)
            nodeItem["ssh_password"] = parse_empty(user_config.password)
            nodeItem["private_key"] = parse_empty(user_config.key_file)
            nodeItem["home_path"] = cluster_config.get_server_conf(server).get("home_path")
            data_dir = cluster_config.get_server_conf(server).get("data_dir")
            redo_dir = cluster_config.get_server_conf(server).get("redo_dir")
            nodeItem["data_dir"] = data_dir if data_dir else os.path.join(cluster_config.get_server_conf(server).get("home_path"), 'store')
            nodeItem["redo_dir"] = redo_dir if redo_dir else os.path.join(cluster_config.get_server_conf(server).get("home_path"), 'store')
            observer_nodes.append(nodeItem)
        sys_tenant_conf = {}
        if len(ob_services) > 0:
            port = cluster_config.get_server_conf(ob_services[0]).get("mysql_port", 2881)
            sys_tenant_conf["password"] = global_conf.get('root_password', '')
            sys_tenant_conf["user"] = 'root@sys'
            obcluster_config["db_host"] = ob_services[0].ip
            obcluster_config["db_port"] = port
            obcluster_config["ob_cluster_name"] = deploy_name
            obcluster_config["tenant_sys"] = sys_tenant_conf
            obcluster_config["servers"] = {"nodes": observer_nodes, "global": {}}
        if len(obproxy_nodes) > 0:
            config={"obcluster": obcluster_config, "obproxy": obproxy_config}
        else:
            config={"obcluster": obcluster_config}
        return config

    def write_obdiag_config(data):
        directory = os.path.dirname(config_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(config_path, 'wb') as f:
            try:
                yaml.dump(data, f)
            except:
                stdio.error('path %s dump obdiag config %s failed.\n' % (config_path, data))

    def copy_check_config():
        obdiag_install_dir = get_option('obdiag_dir')
        init_shell_path = os.path.join(obdiag_install_dir, 'init.sh')
        init_command = 'sh {0}'.format(init_shell_path)
        LocalClient.execute_command(init_command, None, None, None)
    
    def run():
        config_data = get_obdiag_config()
        write_obdiag_config(config_data)
        copy_check_config()

    try:
        if run():
            plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.exception("obdiag config failed")
        return plugin_context.return_false()