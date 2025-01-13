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

import _errno as err


class ConnectCursor(dict):
    def close(self):
        pass


class OcpExpressCursor(object):

    class Response(object):

        def __init__(self, code, content):
            self.code = code
            self.content = content

        def __bool__(self):
            return self.code == 200

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.url_prefix = "http://{ip}:{port}/".format(ip=self.ip, port=self.port)
        self.auth = None

    def status(self, stdio=None):
        resp = self._request('GET', 'api/v1/status', stdio=stdio)
        if resp:
            return resp.content.get("status") == "ok"
        return False

    def init(self, data, stdio=None):
        return self._request("POST", 'api/v1/init', data=data, stdio=stdio)

    def _request(self, method, api, data=None, retry=5, stdio=None):
        url = self.url_prefix + api
        headers = {"Content-Type": "application/json"}
        try:
            if data is not None:
                data = json.dumps(data)
            stdio.verbose('send http request method: {}, url: {}, data: {}'.format(method, url, data))
            resp = requests.request(method, url, auth=self.auth, data=data, verify=False, headers=headers)
            return_code = resp.status_code
            content = resp.content
        except Exception as e:
            if retry:
                retry -= 1
                return self._request(method=method, api=api, data=data, retry=retry, stdio=stdio)
            stdio.exception("")
            return_code = 500
            content = str(e)
        if return_code != 200:
            stdio.verbose("request ocp-express failed: %s" % content)
        try:
            content = json.loads(content.decode())
        except:
            pass
        return self.Response(code=return_code, content=content)


def connect(plugin_context, target_server=None, *args, **kwargs):
    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)
    
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    if target_server:
        servers = [target_server]
        stdio.start_loading('Connect to ocp-express ({})'.format(target_server))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to ocp-express')
    cursors = ConnectCursor()
    for server in servers:
        config = cluster_config.get_server_conf(server)
        username = 'system'
        stdio.verbose('connect ocp-express ({}:{} by user {})'.format(server.ip, config['port'], username))
        cursor = OcpExpressCursor(ip=server.ip, port=config['port'])
        if cursor.status(stdio=stdio):
            cursors[server] = cursor
    if not cursors:
        stdio.error(err.EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return return_true(connect=cursors, cursor=cursors)
