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

import re
import time
import uuid

from const import ENCRYPT_PASSWORD


class Codec(object):

    NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "oceanbase.com")

    @staticmethod
    def encoding_version(version):
        version = re.match("(\d+).(\d+).(\d+).(\d+)", version)
        if version is None:
            raise ValueError("Invalid version")

        ver = 0
        for i, v in enumerate(version.groups()):
            ver |= int(v) << (i * 8)
        return "%08x" % ver
    
    @staticmethod
    def encoding(cid, version):
        ver = Codec.encoding_version(version)
        code = "%08x-%s" % (cid, ver)
        uid = uuid.uuid5(Codec.NAMESPACE, code)
        count = sum(uid.bytes)
        return "%s-%08x-%s" % (uid, cid + count, ver)


def passwd_format(passwd):
    return "'{}'".format(passwd.replace("'", "'\"'\"'"))


def display(plugin_context, cursor, config_encrypted, display_encrypt_password='******', *args, **kwargs):
    stdio = plugin_context.stdio
    if kwargs.get("source_type") != "display":
        stdio.start_loading('Wait for seekdb init')
        time.sleep(5)
        stdio.stop_loading('succeed')
    cluster_config = plugin_context.cluster_config
    if not config_encrypted:
        display_encrypt_password = None
    try:
        while True:
            try:
                server = cursor.fetchone('select * from oceanbase.V$OB_SERVER_STAT', raise_exception=True, exc_level='verbose')
                if not server.get('START_SERVICE_TIME'):
                    time.sleep(3)
                    continue
                break
            except Exception as e:
                code = e.args[0]
                if code != 1146 and code != 4012:
                    raise e
                time.sleep(3)
    except:
        stdio.stop_loading('fail', 'seekdb need bootstarp')


    server = cluster_config.servers[0]
    server_config = cluster_config.get_server_conf(server)
    ip = server.ip
    port = server_config.get('mysql_port', 2881)
    version = cluster_config.version

    stdio.print_list([{'ip': ip, 'version': version, 'port': port}], 
                     ['ip', 'version', 'port'], 
                     lambda x: [x['ip'], x['version'], x['port']], 
                     title=cluster_config.name)

    user = 'root'
    password = cluster_config.get_global_conf().get('root_password', '') if not display_encrypt_password else display_encrypt_password
    cmd = 'obclient -h%s -P%s -uroot %s-Doceanbase -A' % (ip, port, '-p%s ' % passwd_format(password) if password else '')
    stdio.print(cmd)
    
    info_dict = {
        "type": "db",
        "ip": ip,
        "port": port,
        "user": user,
        "password": password,
        "cmd": cmd
    }
    return plugin_context.return_true(info=info_dict)
