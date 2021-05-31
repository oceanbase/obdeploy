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
from glob import glob

from mysqltest_lib import case_filter, succtest
from mysqltest_lib.psmallsource import psmall_source
from mysqltest_lib.psmalltest import psmall_test


def check_test(plugin_context, opt, *args, **kwargs):
    test_set = []
    has_test_point = False
    basename = lambda path: os.path.basename(path)
    dirname =lambda path: os.path.dirname(path)

    if 'all' in opt and opt['all'] and os.path.isdir(os.path.realpath(opt['suite_dir'])):
        opt['suite'] = ','.join(os.listdir(os.path.realpath(opt['suite_dir'])))

    if 'psmall' in opt and opt['psmall']:
        test_set = psmall_test
        opt['source_limit'] = psmall_source
    elif 'suite' not in opt or not opt['suite']:
        if 'test_set' in opt and opt['test_set']:
            test_set = opt['test_set'].split(',')
            has_test_point = True
        else:
            if not 'test_pattern' in opt or not opt['test_pattern']:
                opt['test_pattern'] = '*.test'
            else:
                has_test_point = True
            pat = os.path.join(opt['test_dir'], opt['test_pattern'])
            test_set = [basename(test).rsplit('.', 1)[0] for test in glob(pat)]
    else:
        opt['test_dir_suite'] = [os.path.join(opt['suite_dir'], suite, 't') for suite in opt['suite'].split(',')]
        opt['result_dir_suite'] = [os.path.join(opt['suite_dir'], suite, 'r') for suite in opt['suite'].split(',')]
        has_test_point = True
        for path in opt['test_dir_suite']:
            suitename = basename(dirname(path))
            if 'test_set' in opt and opt['test_set']:
                test_set_tmp = [suitename + '.' + test for test in opt['test_set'].split(',')]
            else:
                if not 'test_pattern' in opt or not opt['test_pattern']:
                    opt['test_pattern'] = '*.test'
                pat = os.path.join(path, opt['test_pattern'])
                test_set_tmp = [suitename + '.' + basename(test).rsplit('.', 1)[0] for test in glob(pat)]

            test_set.extend(test_set_tmp)

    # exclude somt tests.
    if 'exclude' not in opt or not opt['exclude']:
        opt['exclude'] = []
    test_set = filter(lambda k: k not in opt['exclude'], test_set)
    if 'filter' in opt and opt['filter']:
        exclude_list = getattr(case_filter, '%s_list' % opt['filter'], [])
        test_set = filter(lambda k: k not in exclude_list, test_set)

    ##有all参数时重新排序,保证运行case的顺序
    if 'all' in opt and opt['all'] == 'all':
        test_set_suite = filter(lambda k: '.' in k, test_set)
        test_set_suite = sorted(test_set_suite)
        test_set_t = filter(lambda k: k not in test_set_suite, test_set)
        test_set = sorted(test_set_t)
        test_set.extend(test_set_suite)
        if 'succ' in opt and opt['succ'] == 'succ':
            test_set = filter(lambda k: k not in succtest.succ_filter, test_set)
    else:
        test_set = sorted(test_set)

        if 'slices' in opt and opt['slices'] and 'slice_idx' in opt and opt['slice_idx']:
            slices = int(opt['slices'])
            slice_idx = int(opt['slice_idx'])
            test_set = test_set[slice_idx::slices]
    
    opt['test_set'] = test_set
    return plugin_context.return_true(test_set=test_set)
