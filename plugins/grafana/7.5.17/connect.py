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
import time

import requests
from requests.auth import HTTPBasicAuth

from _errno import EC_FAIL_TO_CONNECT


class GrafanaAPICursor(object):

    HEADERS = {"Content-Type": "application/json"}

    def __init__(self, ip, port, user=None, password=None, protocol=None):
        self._update(ip=ip, port=port, user=user,  password=password, protocol=protocol)

    def _update(self, ip, port, user,  password, protocol):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.user = user
        self.password = password
        self.url_prefix = "{protocol}://{ip}:{port}/".format(protocol=protocol, ip=self.ip, port=self.port)
        if self.user:
            self.auth = HTTPBasicAuth(username=self.user, password=self.password)
        else:
            self.auth = None

    def _request(self, method, api, data=None, stdio=None):
        url = self.url_prefix + api
        try:
            if data is not None:
                data = json.dumps(data)
            resp = requests.request(method, url, headers=self.HEADERS, auth=self.auth, data=data, verify=False)
            return_code = resp.status_code
            content = resp.content
        except Exception as e:
            stdio.exception("")
            return_code = 500
            content = str(e)
        if return_code == 200:
            return True
        stdio.verbose("request grafana failed: %s" % content)
        return False

    def connect(self, stdio=None):
        return self._request('GET', 'api/dashboards/tags', stdio=stdio)

    def modify_password(self, grafana_new_pwd, stdio=None):
        if grafana_new_pwd == self.password:
            return True
        if self._request('PUT', 'api/user/password', data={"oldPassword": str(self.password), "newPassword": str(grafana_new_pwd), "confirmNew": str(grafana_new_pwd)}, stdio=stdio):
            self._update(self.ip, self.port, self.user, grafana_new_pwd, self.protocol)
            return True
        return False


def connect(plugin_context, target_server=None, *args, **kwargs):
    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)
    
    cluster_config = plugin_context.cluster_config
    new_cluster_config = kwargs.get("new_cluster_config")
    count = kwargs.get("retry_times", 10)
    stdio = plugin_context.stdio
    clients = plugin_context.clients

    if target_server:
        servers = [target_server]
        stdio.start_loading('Connect to grafana ({})'.format(target_server))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to grafana')
    cursors = {}

    protocol = 'http'
    user = 'admin'
    while count and servers:
        count -= 1
        for server in servers:
            config = cluster_config.get_server_conf(server)
            if config.get('customize_config'):
                if config['customize_config'].get("server"):
                    if config['customize_config']['server'].get('protocol'):
                        protocol = config['customize_config']['server']['protocol']

            if config.get('security'):
                if config['security'].get('admin_user'):
                    user = config['security']['admin_user']

            login_password = config['login_password'] if count % 2 else 'admin'
            stdio.verbose('connect grafana ({}:{} by user {})'.format(server.ip, config['port'], user))
            api_cursor = GrafanaAPICursor(ip=server.ip, port=config['port'], user=user, password=login_password, protocol=protocol)
            if api_cursor.connect(stdio=stdio):
                cursors[server] = api_cursor
        if cursors:
            break
        time.sleep(3)

    if not cursors:
        stdio.error(EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
   
    stdio.stop_loading('succeed')
    return return_true(connect=cursors, cursor=cursors)