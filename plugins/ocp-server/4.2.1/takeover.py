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
import uuid
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
        self.base_url = base_url.strip("/")
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
            raise Exception("takeover precheck failed")
    def get_host_types(self, stdio=None):
        resp = self._request('GET', '/api/v2/compute/hostTypes', stdio=stdio)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to query host types: %s" % msg)

    def create_host_type(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/compute/hostTypes', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to create host type: %s" % msg)

    def list_credentials(self, stdio=None):
        resp = self._request('GET', '/api/v2/profiles/me/credentials', stdio=stdio)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to query credentials: %s" % msg)

    def create_credential(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/profiles/me/credentials', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to create credential: %s" % msg)

    def take_over(self, data, stdio=None):
        resp = self._request('POST', '/api/v2/ob/clusters/takeOver', data=data, stdio=stdio)
        if resp.code == 200:
            return resp.content
        else:
            msg = resp.content
            if 'error' in resp.content and 'message' in resp.content['error']:
                msg = resp.content['error']['message']
            raise Exception("failed to do take over: %s" % msg)

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

def takeover(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    try:
        _do_takeover(plugin_context, *args, **kwargs)
    except Exception as ex:
        stdio.error("do takeover got exception:%s", ex)
        return plugin_context.return_false()

def _do_takeover(plugin_context, *args, **kwargs):
    # init variables, include get obcluster info from deploy config
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    options = plugin_context.options
    stdio = plugin_context.stdio
    stdio.verbose(vars(cluster_config))
    address = getattr(options, 'address', '')
    user = getattr(options, 'user', '')
    password = getattr(options, 'password', '')
    host_type = getattr(options, 'host_type', '')
    credential_name = getattr(options, 'credential_name', '')
    ocp_cursor = OcpCursor(base_url=address, username=user, password=password)
    if len(clients) == 0:
        stdio.error("no available clients")
        return plugin_context.return_false()
    ssh_client = None
    for ssh_client in clients.values():
        if ssh_client != None:
            break
    ssh_config = ssh_client.config
    # query host types, add host type if current host_type is not empty and no matched record in ocp, otherwise use the first one
    host_types = ocp_cursor.get_host_types(stdio=stdio)['data']['contents']
    host_type_id = None
    if host_type == "":
        if len(host_types) > 0:
            host_type_id = host_types[0]['id']
    else:
        for t in host_types:
            if host_type == t['name']:
                host_type_id = t['id']
                break
    if host_type_id is None:
        create_host_type_data = {'name': host_type if host_type is not None else str(uuid.uuid4()).split('-')[-1]}
        host_type_id = ocp_cursor.create_host_type(create_host_type_data, stdio=stdio)['data']['id']
    # query credentials
    credential_id = None
    if credential_name != "":
        credentials = ocp_cursor.list_credentials(stdio=stdio)['data']['contents']
        for credential in credentials:
            if credential['targetType'] == "HOST" and credential['name'] == credential_name:
                stdio.verbose("found credential with id %d", credential['id'])
                credential_id = credential['id']
                break
    if credential_id is None:
        name = credential_name if credential_name != "" else str(uuid.uuid4()).split('-')[-1]
        credential_type = "PRIVATE_KEY"
        if ssh_config.password is not None and ssh_config.password != "":
            credential_type = "PASSWORD"
            pass_phrase = ssh_config.password
        else:
            key_file = ssh_config.key_filename if ssh_config.key_filename is not None else '{0}/.ssh/id_rsa'.format(os.path.expanduser("~"))
            with open(key_file, 'r') as fd:
                pass_phrase = fd.read()
        create_credential_data = {"targetType":"HOST","name":name,"sshCredentialProperty":{"type":credential_type, "username":ssh_config.username,"passphrase":pass_phrase}}
        credential_id = ocp_cursor.create_credential(create_credential_data, stdio=stdio)['data']['id']
    server = cluster_config.servers[0]
    mysql_port = cluster_config.get_global_conf().get("mysql_port")
    root_password = cluster_config.get_global_conf().get("root_password")
    takeover_data = {"switchConfigUrl":True,"connectionMode":"direct","rootSysPassword":root_password,"address":server.ip,"port":mysql_port,"hostInfo":{"kind":"DEDICATED_PHYSICAL_MACHINE","hostTypeId":host_type_id,"sshPort":22,"credentialId":credential_id}}
    proxyro_password = cluster_config.get_global_conf().get("proxyro_password")
    if proxyro_password is not None and proxyro_password != "":
        takeover_data.update({"proxyroPassword": proxyro_password})
    takeover_result = ocp_cursor.take_over(takeover_data, stdio=stdio)
    stdio.verbose("takeover result %s" % takeover_result)
    task_id = takeover_result['data']['id']
    cluster_id = takeover_result['data']['clusterId']
    return plugin_context.return_true(task_id=task_id, cluster_id = cluster_id)
