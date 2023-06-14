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

import time


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
                        lambda x: [x['svr_ip'], x['build_version'].split('_')[0], x['inner_port'], x['zone'], x['status']], title='observer')
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
                    return plugin_context.return_true(info=info_dict)
            except Exception as e:
                code =  e.args[0]
                if code != 1146 and code != 4012:
                    raise e
                time.sleep(3)
    except:
        stdio.stop_loading('fail', 'observer need bootstarp')
    plugin_context.return_false()
