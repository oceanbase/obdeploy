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

import os

from ssh import LocalClient


def check_opt(plugin_context, opt, *args, **kwargs):
    stdio = plugin_context.stdio
    server = opt['test_server']
    obclient_bin = opt['obclient_bin']
    mysqltest_bin = opt['mysqltest_bin']
    reboot_retries = opt['reboot_retries']

    if int(reboot_retries) <= 0:
        stdio.error('invalid reboot-retries')
        return

    if not server:
        stdio.error('test server is None. please use `--test-server` to set')
        return
    ret = LocalClient.execute_command('%s --help' % obclient_bin, stdio=stdio)
    if not ret:
        stdio.error('%s\n%s is not an executable file. please use `--obclient-bin` to set.\nYou may not have obclient installed' % (ret.stderr, obclient_bin))
        return
    ret = LocalClient.execute_command('%s --help' % mysqltest_bin, stdio=stdio)
    if not ret:
        mysqltest_bin = opt['mysqltest_bin'] = 'mysqltest'
        if not LocalClient.execute_command('%s --help' % mysqltest_bin, stdio=stdio):
            stdio.error('%s\n%s is not an executable file. please use `--mysqltest-bin` to set\nYou may not have mysqltest installed' % (ret.stderr, mysqltest_bin))
            return

    if 'suite_dir' not in opt or not os.path.exists(opt['suite_dir']):
        opt['suite_dir'] = os.path.join(os.path.split(__file__)[0], 'test_suite')
        
    if 'all' in opt and opt['all']:
        opt['suite'] = ','.join(os.listdir(opt['suite_dir']))
    elif 'suite' in opt and opt['suite']:
        opt['suite'] = opt['suite'].strip()

    if 'slb' in opt:
        opt['slb_host'], opt['slb_id'] = opt['slb'].split(',')

    if 'exclude' in opt and opt['exclude']:
        opt['exclude'] = opt['exclude'].split(',')

    cluster_config = plugin_context.cluster_config

    is_obproxy = opt["component"].startswith("obproxy")
    if is_obproxy:
        intersection = list({'oceanbase', 'oceanbase-ce'}.intersection(set(cluster_config.depends)))
        if not intersection:
            stdio.warn('observer config not in the depends.')
            return
        ob_component = intersection[0]
        global_config = cluster_config.get_depend_config(ob_component)
    else:
        global_config = cluster_config.get_global_conf()
    cursor = opt['cursor']
    opt['_enable_static_typing_engine'] = None
    if '_enable_static_typing_engine' in global_config:
        stdio.verbose('load engine from config')
        opt['_enable_static_typing_engine'] = global_config['_enable_static_typing_engine']
    else:
        try:
            sql = "select value from oceanbase.__all_virtual_sys_parameter_stat where name like '_enable_static_typing_engine';"
            stdio.verbose('execute sql: {}'.format(sql))
            cursor.execute(sql)
            ret = cursor.fetchone()
            stdio.verbose('query engine ret: {}'.format(ret))
            if ret:
                opt['_enable_static_typing_engine'] = ret.get('value')
        except:
            stdio.exception('')
    stdio.verbose('_enable_static_typing_engine: {}'.format(opt['_enable_static_typing_engine']))
    return plugin_context.return_true()
