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


def takeover(plugin_context, cursors=None, *args, **kwargs):
    try:
        # init variables, include get obcluster info from deploy config
        cluster_config = plugin_context.cluster_config
        clients = plugin_context.clients
        options = plugin_context.options
        stdio = plugin_context.stdio
        stdio.verbose(vars(cluster_config))
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
        cursors = plugin_context.get_return('connect').get_return('cursor') if not cursors else cursors
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
        return plugin_context.return_true(task_id=task_id, cluster_id=cluster_id)
    except Exception as ex:
        stdio.error("do takeover got exception:%s", ex)
        return plugin_context.return_false()