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
from tool import NetUtil


class ObConfigServerCursor(object):

    def __init__(self, ip, port,  username=None, password=None):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.url_prefix = "http://{ip}:{port}/".format(ip=self.ip, port=self.port)
        if self.username:
            self.auth = HTTPBasicAuth(username=username, password=password)
        else:
            self.auth = None
        self._status = None
        self._status_error = ''

    @property
    def status(self):
        if self._status is None:
            self._status, self._status_error = self._request('get', 'services?Action=GetObProxyConfig')
        return self._status

    @property
    def status_error(self):
        return self._status_error

    def _request(self, method, api):
        url = self.url_prefix + api
        try:
            response = requests.request(method, url)
            if json.loads(response.content)['Code'] == 200:
                return True, None
            else:
                return False, 'response code: %s' % str(json.loads(response.content)['Code'])
        except Exception as e:
            return False, str(e)



def connect(plugin_context, *args, **kwargs):
    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)
    
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global_ret = True
    cursors = {}
    stdio.start_loading('Connect to ob-configserver')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        port = server_config['listen_port']
        ip = server.ip
        api_cursor = ObConfigServerCursor(ip=ip, port=port)
        if not api_cursor.status:
            stdio.verbose("{server}: request ob-configserver failed: {error}".format(server=server, error=api_cursor.status_error))
            global_ret = False
        else:
            cursors[server] = api_cursor

    if global_ret:
        stdio.stop_loading('succeed')
        return return_true(connect=cursors, cursor=cursors)
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
