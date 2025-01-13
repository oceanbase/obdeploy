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


def takeover(plugin_context, cursors=None, *args, **kwargs):
    try:
        # init variables, include get obcluster info from deploy config
        cluster_config = plugin_context.cluster_config
        clients = plugin_context.clients
        options = plugin_context.options
        stdio = plugin_context.stdio
        host_type = getattr(options, 'host_type', '')
        credential_name = getattr(options, 'credential_name', '')
        if len(clients) == 0:
            stdio.error("no available clients")
            return plugin_context.return_false()
        ssh_client = None
        for ssh_client in clients.values():
            if ssh_client != None:
                break
        ssh_config = ssh_client.config
        cursors = plugin_context.get_return('takeover_connect').get_return('cursor') if not cursors else cursors
        cursor = cursors[cluster_config.servers[0]]
        # query host types, add host type if current host_type is not empty and no matched record in ocp, otherwise use the first one
        host_types = cursor.get_host_types(stdio=stdio)['data']['contents']
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
            host_type_id = cursor.create_host_type(create_host_type_data, stdio=stdio)['data']['id']
        # query credentials
        credential_id = None
        if credential_name != "":
            credentials = cursor.list_credentials(stdio=stdio)['data']['contents']
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
                key_file = ssh_config.key_filename if ssh_config.key_filename is not None else '{0}/.ssh/id_rsa'.format(
                    os.path.expanduser("~"))
                with open(key_file, 'r') as fd:
                    pass_phrase = fd.read()
            create_credential_data = {"targetType": "HOST", "name": name,
                                      "sshCredentialProperty": {"type": credential_type,
                                                                "username": ssh_config.username,
                                                                "passphrase": pass_phrase}}
            credential_id = cursor.create_credential(create_credential_data, stdio=stdio)['data']['id']
        server = cluster_config.servers[0]
        mysql_port = cluster_config.get_global_conf().get("mysql_port")
        root_password = cluster_config.get_global_conf().get("root_password")
        takeover_data = {"switchConfigUrl": True, "connectionMode": "direct", "rootSysPassword": root_password,
                         "address": server.ip, "port": mysql_port,
                         "hostInfo": {"kind": "DEDICATED_PHYSICAL_MACHINE", "hostTypeId": host_type_id, "sshPort": ssh_config.port,
                                      "credentialId": credential_id}}
        proxyro_password = cluster_config.get_global_conf().get("proxyro_password")
        if proxyro_password is not None and proxyro_password != "":
            takeover_data.update({"proxyroPassword": proxyro_password})
        takeover_result = cursor.take_over(takeover_data, stdio=stdio)
        stdio.verbose("takeover result %s" % takeover_result)
        task_id = takeover_result['data']['id']
        cluster_id = takeover_result['data']['clusterId']
        stdio.print("takeover task successfully submitted to ocp, you can check task at %s/task/%d" % (getattr(options, 'address', ''), task_id))
        return plugin_context.return_true(task_id=task_id, cluster_id=cluster_id)
    except Exception as ex:
        stdio.error("do takeover got exception:%s", ex)
        return plugin_context.return_false()
