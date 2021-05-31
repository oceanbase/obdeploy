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
            stdio.error('%s\n%s is not an executable file. please use `--mysqltest-bin` to set\nYou may not have obclient installed' % (ret.stderr, mysqltest_bin))
            return

    if 'suite_dir' not in opt or not os.path.exists(opt['suite_dir']):
        opt['suite_dir'] = os.path.join(os.path.split(__file__)[0], 'test_suite')
        
    if 'all' in opt and opt['all']:
        opt['suite'] = ','.join(os.listdir(opt['suite_dir']))
    elif 'suite' in opt and opt['suite']:
        opt['suite'] = opt['suite'].strip()

    if 'slb' in opt:
        opt['slb_host'], opt['slb_id'] = opt['slb'].split(',')
    
    return plugin_context.return_true()
