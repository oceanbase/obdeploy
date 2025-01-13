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
import json
from tool import YamlLoader, FileUtil
from subprocess import call, Popen, PIPE

OBAG_BASE_DEFAULT_CONFIG = {
  "OBDIAG": {
    "BASIC": {
      "config_backup_dir": "/tmp/oceanbase-diagnostic-tool/conf",
      "file_number_limit": 20,
      "file_size_limit": "2G"
    },
    "LOGGER": {
      "file_handler_log_level": "DEBUG",
      "log_dir": "/tmp/oceanbase-diagnostic-tool/log",
      "log_filename": "obdiag.log",
      "log_level": "INFO",
      "mode": "obdiag",
      "stdout_handler_log_level": "INFO"
    }
  }
}

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
    obdiag_install_dir = get_option('obdiag_dir')
    config_path = os.path.join(obdiag_install_dir, 'conf/config.yml')
    
    def get_obdiag_config():
        with FileUtil.open(config_path) as f:
            data = YamlLoader(stdio=stdio).load(f)
        base_config = data["OBDIAG"]
        if base_config is None:
            base_config = OBAG_BASE_DEFAULT_CONFIG
        ocp_config = data["OCP"]
        obcluster_config = data["OBCLUSTER"]
        ob_services = cluster_config.servers
        nodes = []
        for server in ob_services:
            nodeItem = {}
            nodeItem["ip"] = server.ip
            nodeItem["port"] = parse_empty(user_config.port)
            nodeItem["user"] = parse_empty(user_config.username)
            nodeItem["password"] = parse_empty(user_config.password)
            nodeItem["private_key"] = parse_empty(user_config.key_file)
            nodeItem["home_path"] = cluster_config.get_server_conf(server).get("home_path")
            nodes.append(nodeItem)
        nodes_config = nodes

        try:
            component = get_option('component')
        except:
            component = "oceanbase-ce"
        if len(ob_services) > 0:
            server_config = cluster_config.get_server_conf(server)
            port = 2881
            if component in ["oceanbase", "oceanbase-ce"]:
                port = server_config.get("mysql_port")
            elif component in ["obproxy", "obproxy-ce"]:
                port = server_config.get("listen_port")
            obcluster_config["cluster_name"] = deploy_name
            obcluster_config["host"] = ob_services[0].ip
            obcluster_config["port"] = port
            try:
                obcluster_config["user"] = get_option('user')
            except:
                obcluster_config["user"] = 'root'
            try:
                obcluster_config["port"] = get_option('port')
            except:
                obcluster_config["port"] = 2881
            try:
                obcluster_config["password"] = get_option('password')
            except:
                obcluster_config["password"] = ""
            if global_conf.get('root_password') is not None:
                obcluster_config["password"] = global_conf.get('root_password')
            if global_conf.get('mysql_port') is not None:
                obcluster_config["port"] = global_conf.get('mysql_port')
        checker_config = {}
        checker_config["ignore_obversion"]=False
        checker_config["report"] = {}
        if "report_path" in checker_config["report"]:
            checker_config["report"]["report_path"] = get_option('report_path')
        else:
            checker_config["report"]["report_path"]= "./check_report/"
        checker_config["report"]["export_type"] = "table"
        checker_config["package_file"] = obdiag_install_dir+"/check_package.yaml"
        checker_config["tasks_base_path"] = obdiag_install_dir+"/handler/checker/tasks/"
        config={
            "OBDIAG": base_config,
            "OCP": ocp_config,
            "OBCLUSTER": obcluster_config,
            "NODES":nodes_config,
            "CHECK": checker_config
        }
        return config

    def dump_obdiag_config(data):
        with open(config_path, 'wb') as f:
            try:
                yaml.dump(data, f)
            except:
                stdio.error('path %s dump obdiag config %s failed.\n' % (config_path, data))
    
    def run():
        config_data = get_obdiag_config()
        dump_obdiag_config(config_data)
        p = None
        return_code = 255
        try:
            p = Popen("get obdiag config", shell=True)
            return_code = p.wait()
        except:
            stdio.exception("")
            if p:
                p.kill()
        stdio.verbose('exit code: {}'.format(return_code))
        return return_code == 0

    try:
        if run():
            plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.exception("obdiag gather log failded")
        return plugin_context.return_false()