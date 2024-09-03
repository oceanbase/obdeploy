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

import re
import time
import uuid


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


def display(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading('Wait for observer init')
    cluster_config = plugin_context.cluster_config
    try:
        while True:
            try:
                servers = cursor.fetchall('select * from oceanbase.__all_server', raise_exception=True, exc_level='verbose')
                if servers:
                    stdio.print_list(servers, ['ip', 'version', 'port', 'zone', 'status'],
                        lambda x: [x['svr_ip'], x['build_version'].split('_')[0], x['inner_port'], x['zone'], x['status']], title=cluster_config.name)
                    user = 'root'
                    password = cluster_config.get_global_conf().get('root_password', '')
                    cmd = 'obclient -h%s -P%s -u%s %s-Doceanbase -A' % (servers[0]['svr_ip'], servers[0]['inner_port'], user, '-p%s ' % passwd_format(password) if password else '')
                    stdio.print(cmd)
                    stdio.stop_loading('succeed')
                    info_dict = {
                        "type": "db",
                        "ip": servers[0]['svr_ip'],
                        "port": servers[0]['inner_port'],
                        "user": user,
                        "password": password,
                        "cmd": cmd
                    }

                    var = cursor.fetchone('select unix_timestamp(gmt_create) as gmt_create from oceanbase.__all_virtual_sys_variable limit 1',  raise_exception=True, exc_level='verbose')
                    if var:
                        cid = int(var['gmt_create'] * 1000)
                        unique_id = Codec.encoding(cid, servers[0]['build_version'])
                        stdio.print('cluster unique id: %s\n' % unique_id)
                    return plugin_context.return_true(info=info_dict, unique_id=unique_id)
            except Exception as e:
                code =  e.args[0]
                if code != 1146 and code != 4012:
                    raise e
                time.sleep(3)
    except:
        stdio.stop_loading('fail', 'observer need bootstarp')
    stdio.exception('')
    plugin_context.return_false()
