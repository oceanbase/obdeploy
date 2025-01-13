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

from ssh import LocalClient


def check_opt(plugin_context, env, *args, **kwargs):
    opt = env
    stdio = plugin_context.stdio
    server = opt['test_server']
    obclient_bin = opt['obclient_bin']
    mysqltest_bin = opt['mysqltest_bin']
    reboot_retries = opt['reboot_retries']

    if int(reboot_retries) <= 0:
        stdio.error('invalid reboot-retries')
        return

    case_filter = opt.get('case_filter')
    default_case_filter = './mysql_test/filter.py'
    if case_filter is None and os.path.exists(default_case_filter):
        stdio.verbose('case-filter not set and {} exists, use it'.format(default_case_filter))
        opt['case_filter'] = default_case_filter

    case_filter = opt.get('reboot_cases')
    default_reboot_case = './mysql_test/rebootcases.py'
    if case_filter is None and os.path.exists(default_reboot_case):
        stdio.verbose('reboot-cases not set and {} exists, use it'.format(default_reboot_case))
        opt['reboot_cases'] = default_reboot_case

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
        ob_component = opt["component"]
        global_config = cluster_config.get_global_conf()
    opt['is_business'] = 1 if ob_component == 'oceanbase' else 0
    cursor = plugin_context.get_return('connect').get_return('cursor')
    opt['_enable_static_typing_engine'] = None
    if '_enable_static_typing_engine' in global_config:
        stdio.verbose('load engine from config')
        opt['_enable_static_typing_engine'] = global_config['_enable_static_typing_engine']
    else:
        sql = "select value from oceanbase.__all_virtual_sys_parameter_stat where name like '_enable_static_typing_engine';"
        ret = cursor.fetchone(sql)
        if ret is False:
            return
        stdio.verbose('query engine ret: {}'.format(ret))
        if ret:
            opt['_enable_static_typing_engine'] = ret.get('value')
    stdio.verbose('_enable_static_typing_engine: {}'.format(opt['_enable_static_typing_engine']))
    return plugin_context.return_true()
