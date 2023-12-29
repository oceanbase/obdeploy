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
import os

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
        stdio.verbose('send http request method: {}, url: {}, data: {}'.format(method, url, data))
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
    grafana_default_pwd = 'admin'
    for server in servers:
        config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = config['home_path']
        if config.get('customize_config'):
            if config['customize_config'].get("server"):
                if config['customize_config']['server'].get('protocol'):
                    protocol = config['customize_config']['server']['protocol']

        if config.get('security'):
            if config['security'].get('admin_user'):
                user = config['security']['admin_user']
        
        touch_path = os.path.join(home_path, 'run/.grafana')
        if client.execute_command("ls %s" % touch_path):
            grafana_default_pwd = config['login_password']

        stdio.verbose('connect grafana ({}:{} by user {})'.format(server.ip, config['port'], user))
        api_cursor = GrafanaAPICursor(ip=server.ip, port=config['port'], user=user, password=grafana_default_pwd, protocol=protocol)
        cursors[server] = api_cursor
    
    if not cursors:
        stdio.error(EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
   
    stdio.stop_loading('succeed')
    return return_true(connect=cursors, cursor=cursors)