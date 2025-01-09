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
import requests
from requests.auth import HTTPBasicAuth

from _errno import EC_FAIL_TO_CONNECT


class ObagentAPICursor(object):
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
        return self._request('GET', 'api/v1/agent/status', stdio=stdio)

    def reload(self, data, stdio=None):
        return self._request('POST', 'api/v1/module/config/update', data, stdio=stdio)

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
        stdio.verbose("request obagent failed: %s" % content)
        return False


def connect(plugin_context, target_server=None, *args, **kwargs):
    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)
    
    cluster_config = plugin_context.cluster_config
    new_cluster_config = kwargs.get("new_cluster_config")
    stdio = plugin_context.stdio
    if target_server:
        servers = [target_server]
        stdio.start_loading('Connect to Obagent ({})'.format(target_server))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to Obagent')
    cursors = {}
    count = kwargs.get("retry_times", 10)

    while count and servers:
        count -= 1
        for server in servers:
            config = cluster_config.get_server_conf(server)
            ssl = False
            username = ''
            if config.get('http_basic_auth_user'):
                username = config['http_basic_auth_user']
            new_config = None
            if new_cluster_config:
                new_config = new_cluster_config.get_server_conf(server)
                if new_config:
                    new_password = new_config['http_basic_auth_password']
            password = config.get('http_basic_auth_password', '')
            password = new_password if new_config and count % 2 else password

            stdio.verbose('connect obagent ({}:{} by user {})'.format(server.ip, config['mgragent_http_port'], username))
            api_cursor = ObagentAPICursor(ip=server.ip, port=config['mgragent_http_port'], username=username, password=password,
                                          ssl=ssl)
            if api_cursor.connect(stdio=stdio):
                cursors[server] = api_cursor
    if not cursors:
        stdio.error(EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return return_true(connect=cursors, cursor=cursors)
