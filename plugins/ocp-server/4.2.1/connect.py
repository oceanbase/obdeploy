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
import time

import _errno as err


class OcpServerCursor(object):

    class Response(object):

        def __init__(self, code, content):
            self.code = code
            self.content = content

        def __bool__(self):
            return self.code == 200

    def __init__(self, ip, port, username=None, password=None):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.url_prefix = "http://{ip}:{port}/".format(ip=self.ip, port=self.port)
        if self.username:
            self.auth = HTTPBasicAuth(username=username, password=password)
        else:
            self.auth = None

    def status(self, stdio=None):
        ocp_status_ok = False
        now = time.time()
        check_wait_time = 300
        count = 0
        while time.time() - now < check_wait_time:
            stdio.verbose("query ocp to check...")
            count += 1
            resp = self._request('GET', 'api/v2/time', stdio=stdio)
            try:
                if resp.code == 200 or count >= 10:
                    ocp_status_ok = True
                    break
            except Exception:
                stdio.verbose("ocp still not active")
            time.sleep(3)
        if ocp_status_ok:
            stdio.verbose("check ocp server status ok")
            return True
        else:
            stdio.verbose("OCP is still not working properly, check failed.")
            return True

    def info(self, stdio=None):
        resp = self._request('GET', 'api/v2/info', stdio=stdio)
        if resp.code == 200:
            return resp.content

    def task_over_precheck(self, data, stdio=None):
        resp = self._request('POST', 'api/v2/ob/clusters/takeOverPreCheck', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content

    def compute_host_types(self, data, stdio=None):
        resp = self._request('POST', 'api/v2/compute/hostTypes', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content

    def profiles_credentials(self, data, stdio=None):
        resp = self._request('POST', 'api/v2/profiles/me/credentials', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content

    def task_over(self, data, stdio=None):
        resp = self._request('POST', 'api/v2/ob/clusters/takeOver', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content

    def _request(self, method, api, data=None, retry=5, stdio=None):
        url = self.url_prefix + api
        headers = {"Content-Type": "application/json"}
        try:
            if data is not None:
                data = json.dumps(data)
            stdio.verbose('send http request method: {}, url: {}, data: {}'.format(method, url, data))
            resp = requests.request(method, url, data=data, verify=False, headers=headers, auth=self.auth)
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
            stdio.verbose("request ocp-server failed: %s" % content)
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
        stdio.start_loading('Connect to ocp-server ({})'.format(target_server))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to ocp-server')
    cursors = {}
    for server in servers:
        config = cluster_config.get_server_conf(server)
        username = 'admin'
        password = config['admin_password']
        stdio.verbose('connect ocp-server ({}:{} by user {})'.format(server.ip, config['port'], username))
        cursor = OcpServerCursor(ip=server.ip, port=config['port'], username=username, password=password)
        if cursor.status(stdio=stdio):
            cursors[server] = cursor
    if not cursors:
        stdio.error(err.EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return return_true(connect=cursors, cursor=cursors)

