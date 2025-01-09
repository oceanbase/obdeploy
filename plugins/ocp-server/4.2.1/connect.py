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


class OcpCursor(object):

    class Response(object):

        def __init__(self, code, content):
            self.code = code
            self.content = content

        def __bool__(self):
            return self.code == 200

    def __init__(self, ip=None, port=None, username=None, password=None, component_name=None, stdio=None):
        self.auth = None
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.url_prefix = "http://{ip}:{port}".format(ip=self.ip, port=self.port)
        self.component_name = component_name
        if self.username:
            self.auth = HTTPBasicAuth(username=username, password=password)
        self.stdio = stdio
        self.stdio.verbose('connect {} ({}:{} by user {})'.format(component_name, ip, port, username))

    def status(self, stdio=None):
        ocp_status_ok = False
        now = time.time()
        check_wait_time = 300
        count = 0
        while time.time() - now < check_wait_time and count < 10:
            stdio.verbose("query ocp to check...")
            count += 1
            resp = self._request('GET', '/api/v2/time', stdio=stdio)
            try:
                if resp.code == 200:
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
            return False

    def info(self, stdio=None):
        resp = self._request('GET', '/api/v2/info', stdio=stdio, auth=self.auth)
        if resp.code == 200:
            return resp.content

    def upload_packages(self, files, stdio=None):
        resp = self._request('POST', '/api/v2/software-packages', files=files, stdio=stdio, auth=self.auth)
        if resp.code == 200:
            return resp.content

    def take_over_precheck(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/ob/clusters/takeOverPreCheck', data=data, stdio=stdio, auth=self.auth)
        if resp.code == 200:
            return resp.content

    def get_host_types(self, stdio=None):
        resp = self._request('GET', '/api/v2/compute/hostTypes', stdio=stdio, auth=self.auth)
        if resp.code == 200:
            return resp.content

    def create_host_type(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/compute/hostTypes', data=data, stdio=stdio, auth=self.auth)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to create host type: %s" % msg)

    def list_credentials(self, stdio=None):
        resp = self._request('GET', '/api/v2/profiles/me/credentials', stdio=stdio, auth=self.auth)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to query credentials: %s" % msg)

    def create_credential(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/profiles/me/credentials', data=data, stdio=stdio, auth=self.auth)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to create credential: %s" % msg)

    def take_over(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/ob/clusters/takeOver', data=data, stdio=stdio, auth=self.auth)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to do take over: %s" % msg)

    def _request(self, method, api, data=None, files=None, retry=5, stdio=None, auth=None):
        url = self.url_prefix + api
        headers = {'Content-Type': 'application/json'} if not files else {}
        try:
            if data is not None:
                data = json.dumps(data)
            stdio.verbose('send http request method: {}, url: {}, data: {}, files: {}'.format(method, url, data, files))
            resp = requests.request(method, url, data=data, files=files, verify=False, headers=headers, auth=auth)
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
            stdio.verbose("request %s failed: %s" % (self.component_name, content))
        try:
            content = json.loads(content.decode())
        except:
            pass
        return self.Response(code=return_code, content=content)


class OcpTakeOverCursor(OcpCursor):
    def __init__(self, address, user, password, component_name, stdio=None):
        super(OcpCursor, self).__init__()
        self.url_prefix = address.rstrip('/')
        self.username = user
        self.password = password
        self.component_name = component_name
        if self.username:
            self.auth = HTTPBasicAuth(username=user, password=password)
        self.stdio = stdio


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
        stdio.start_loading('Connect to {} ({})'.format(cluster_config.name, target_server))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to %s' % cluster_config.name)
    cursors = {}
    while count and servers:
        count -= 1
        for server in servers:
            config = cluster_config.get_server_conf(server)
            username = 'admin'
            password = config['admin_password']

            new_config = None
            if new_cluster_config:
                new_config = new_cluster_config.get_server_conf(server)
                if new_config:
                    new_password = new_config['admin_password']
            password = new_password if new_config and count % 2 else password

            port = config['port']
            cursor = OcpCursor(ip=server.ip, port=port, username=username, password=password, component_name=cluster_config.name, stdio=stdio)
            if cursor.status(stdio=stdio):
                cursors[server] = cursor
    if not cursors:
        stdio.error(err.EC_FAIL_TO_CONNECT.format(component='ocp-server-ce'))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return return_true(connect=cursors, cursor=cursors)

