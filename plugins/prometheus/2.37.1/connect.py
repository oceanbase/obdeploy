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
import requests
from requests.auth import HTTPBasicAuth

from _errno import EC_FAIL_TO_CONNECT


class PrometheusAPICursor(object):
    cmd_template = '{protocol}://{ip}:{port}/{suffix}'

    def __init__(self, ip, port, username=None, password=None, ssl=False):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.ssl = ssl
        protocol = 'https' if ssl else 'http'
        self.url_prefix = "{protocol}://{ip}:{port}/".format(protocol=protocol, ip=self.ip, port=self.port)
        if self.username:
            self.auth = HTTPBasicAuth(username=username, password=password)
        else:
            self.auth = None

    def connect(self, stdio=None):
        return self._request('GET', '-/healthy', stdio=stdio)

    def reload(self, stdio=None):
        return self._request('POST', '-/reload', stdio=stdio)

    def _request(self, method, api, data=None, stdio=None):
        url = self.url_prefix + api
        stdio.verbose('send http request method: {}, url: {}, data: {}'.format(method, url, data))
        try:
            if data is not None:
                data = json.dumps(data)
            resp = requests.request(method, url, auth=self.auth, data=data, verify=False)
            return_code = resp.status_code
            content = resp.content
        except Exception as e:
            stdio.exception("")
            return_code = 500
            content = str(e)
        if return_code == 200:
            return True
        stdio.verbose("request prometheus failed: %s" % content)
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
    if target_server:
        servers = [target_server]
        stdio.start_loading('Connect to Prometheus ({})'.format(target_server))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to Prometheus')
    cursors = {}
    while count and servers:
        count -= 1
        for server in servers:
            config = cluster_config.get_server_conf(server)
            ssl = False
            username = None
            password = None
            if config.get('basic_auth_users'):
                username, password = list(config['basic_auth_users'].items())[0]

            new_config = None
            if new_cluster_config:
                new_config = new_cluster_config.get_server_conf(server)
                if new_config:
                    new_username, new_password = list(new_config['basic_auth_users'].items())[0]
            password = new_password if new_config and count % 2 else password

            if config.get('web_config', {}).get('tls_server_config'):
                if config['web_config']['tls_server_config'] and config['web_config']['tls_server_config'].get('cert_file'):
                    ssl = True
            stdio.verbose('connect prometheus ({}:{} by user {})'.format(server.ip, config['port'], username))
            api_cursor = PrometheusAPICursor(ip=server.ip, port=config['port'], username=username, password=password,
                                             ssl=ssl)
            if api_cursor.connect(stdio=stdio):
                cursors[server] = api_cursor
    if not cursors:
        stdio.error(EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return return_true(connect=cursors, cursor=cursors)
