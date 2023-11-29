# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2023 OceanBase
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
import re
import time
import json
import requests
from _rpm import Version
from copy import deepcopy
from requests.auth import HTTPBasicAuth

from tool import Cursor, FileUtil, YamlLoader
from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN

class OcpCursor(object):

    class Response(object):

        def __init__(self, code, content):
            self.code = code
            self.content = content

        def __bool__(self):
            return self.code == 200

    def __init__(self, base_url="http://localhost:8080", username=None, password=None):
        self.base_url = base_url.strip('/')
        self.auth = None
        self.username=username
        self.password=password
        if self.username:
            self.auth = HTTPBasicAuth(username=username, password=password)

    def status(self, stdio=None):
        resp = self._request('GET', '/api/v2/time', stdio=stdio)
        ocp_status_ok = False
        now = time.time()
        check_wait_time = 180
        while time.time() - now < check_wait_time:
            stdio.verbose("query ocp to check...")
            try:
                if resp.code == 200:
                    ocp_status_ok = True
                    break
            except Exception:
                stdio.verbose("ocp still not active")
            time.sleep(5)
        if ocp_status_ok:
            stdio.verbose("check ocp server status ok")
            return True
        else:
            stdio.verbose("ocp still not ok, check failed")
            raise Exception("ocp still not ok, check failed")

    def info(self, stdio=None):
        resp = self._request('GET', '/api/v2/info', stdio=stdio)
        if resp.code == 200:
            return resp.content
        else:
            raise Exception("failed to query ocp info")

    def take_over_precheck(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/ob/clusters/takeOverPreCheck', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content['error']['message']
            raise Exception("takeover precheck failed %s" % msg)

    def compute_host_types(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/compute/hostTypes', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content

    def profiles_credentials(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/profiles/me/credentials', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content

    def take_over(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/ob/clusters/takeOver', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content

    def _request(self, method, api, data=None, retry=5, stdio=None):
        url = self.base_url + api
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

def takeover_precheck(plugin_context, *args, **kwargs):
    # init variables, include get obcluster info from deploy config
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    options = plugin_context.options
    stdio = plugin_context.stdio
    stdio.verbose(vars(cluster_config))
    address = getattr(options, 'address', '')
    user = getattr(options, 'user', '')
    password = getattr(options, 'password', '')
    ocp_cursor = OcpCursor(base_url=address, username=user, password=password)
    ocp_info = ocp_cursor.info(stdio=stdio)
    stdio.verbose("get ocp info %s", ocp_info)
    ocp_version = Version(ocp_info['buildVersion'].split("_")[0])
    if ocp_version < Version("4.2.0"):
        stdio.error("unable to export obcluster to ocp, ocp version must be at least 4.2.0")
        return plugin_context.return_false(ocp_version=ocp_version)
    server = cluster_config.servers[0]
    mysql_port = cluster_config.get_global_conf().get("mysql_port")
    root_password = cluster_config.get_global_conf().get("root_password")
    if root_password is None or root_password == "":
        stdio.error("unable to export obcluster to ocp, root password is empty")
        return plugin_context.return_false(ocp_version=ocp_version)
    precheck_data = {"connectionMode":"direct","address":server.ip,"port":mysql_port,"rootSysPassword":root_password}
    proxyro_password = cluster_config.get_global_conf().get("proxyro_password")
    if proxyro_password is not None and proxyro_password != "":
        precheck_data.update({"proxyroPassword": proxyro_password})
    try:
        precheck_result = ocp_cursor.take_over_precheck(precheck_data, stdio=stdio)
        stdio.verbose("precheck result %s" % precheck_result)
    except Exception as ex:
        return plugin_context.return_false(exception=ex)
    return plugin_context.return_true(ocp_version=ocp_version)
