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
import sys
import re
from glob import glob

import tool
from mysqltest_lib import succtest


def find_tag_test_with_file_pat(file_pattern, flag_pattern, tag, filelist):
    for test in glob(file_pattern):
        if "test_suite/" in test:
            if os.path.dirname(test).split('/')[-2] == tag:
                filelist.append(test)
                continue
        test_file = tool.FileUtil.open(test, 'rb')
        line_num = 0
        line = test_file.readline().decode('utf-8', 'ignore')
        while line and line_num <= 30:
            line_num += 1
            matchobj = re.search(flag_pattern, line)
            if matchobj:
                tag_set = line.split(':')[1].split(',')
                for tag_tmp in tag_set:
                    tag_t = tag_tmp.strip()
                    if tag.lower() == tag_t.lower():
                        filelist.append(test)
            line = test_file.readline().decode('utf-8', 'ignore')


def find_tag_tests(opt, flag_pattern, tags):
    filelist = []
    for tag in tags:
        test_pattern = os.path.join(opt['test_dir'], "*.test")
        find_tag_test_with_file_pat(test_pattern, flag_pattern, tag, filelist)
        test_pattern = os.path.join(opt['suite_dir'], "*/t/*.test")
        find_tag_test_with_file_pat(test_pattern, flag_pattern, tag, filelist)
    return filelist


def test_name(test_file):
    if "test_suite/" in test_file:
        suite_name = os.path.dirname(test_file).split('/')[-2]
        base_name = os.path.basename(test_file).rsplit('.')[0]
        return suite_name + '.' + base_name
    else:
        base_name = os.path.basename(test_file).rsplit('.')[0]
        return base_name


def check_test(plugin_context, env, *args, **kwargs):
    opt = env
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    tags = []
    regress_suites = []
    if opt.get('tags'):
        tags = opt['tags'].split(',')
    if opt.get('regress_suite'):
        regress_suites = opt['regress_suite'].split(',')
    test_set = []
    has_test_point = False
    basename = lambda path: os.path.basename(path)
    dirname =lambda path: os.path.dirname(path)

    get_variable_from_python_file = plugin_context.get_variable("get_variable_from_python_file")

    if 'all' in opt and opt['all'] and os.path.isdir(os.path.realpath(opt['suite_dir'])):
        opt['suite'] = ','.join(os.listdir(os.path.realpath(opt['suite_dir'])))
    if 'psmall' in opt and opt['psmall']:
        test_set = get_variable_from_python_file(
            opt.get('psmall_test'), 'psmall_test', default_file='psmalltest.py', default_value=[], stdio=stdio)
        opt['source_limit'] = get_variable_from_python_file(
            opt.get('psmall_source'), 'psmall_source', default_file='psmallsource.py', default_value={}, stdio=stdio)
        has_test_point = True
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
        if "all" in opt and opt["all"]:
            pat = os.path.join(opt['test_dir'], "*.test")
            test_set_t = [basename(test).rsplit('.', 1)[0] for test in glob(pat)]
            test_set.extend(test_set_t)
    if opt["cluster_mode"]:
        opt["filter"] = opt["cluster_mode"]
    else:
        opt["filter"] = 'c'
        if opt.get("java"):
            opt["filter"] = 'j'
        if opt.get("ps"):
            opt["filter"] = opt["filter"] + 'p'
            opt['ps_protocol'] = True
        if opt["component"].startswith("obproxy"):
            opt["filter"] = 'proxy'
        else:
            test_zone = cluster_config.get_server_conf(opt['test_server'])['zone']
            query = plugin_context.get_variable('query_sql')
            cursor = plugin_context.get_return('connect').get_return('cursor')
            ret = cursor.fetchone(query)
            if ret is False:
                return
            if ret:
                primary_zone = ret.get('zone', '')
            if test_zone != primary_zone:
                opt["filter"] = 'slave'
    if regress_suites:
        suite2tags = get_variable_from_python_file(opt.get('regress_suite_map'), 'suite2tags', default_file='regress_suite_map.py', default_value={}, stdio=stdio)
        composite_suite = get_variable_from_python_file(opt.get('regress_suite_map'), 'composite_suite', default_file='regress_suite_map.py', default_value={}, stdio=stdio)

        for suitename in regress_suites:
            if suitename in composite_suite.keys():
                regress_suite_list = composite_suite[suitename].split(',')
            else:
                regress_suite_list = [suitename]
            for name in regress_suite_list:
                if name in suite2tags.keys():
                    if suite2tags[name]:
                        tags.extend(suite2tags[name].split(','))
                else:
                    tags.append(name)
        tags = list(set(tags))
    if tags:
        stdio.verbose('running mysqltest by tag, all tags: {}'.format(tags))
        support_test_tags = get_variable_from_python_file(
            opt.get('test_tags'), 'test_tags', default_file='test_tags.py', default_value=[], stdio=stdio)
        support_test_tags = list(set(support_test_tags).union(set(os.listdir(os.path.join(opt["suite_dir"])))))
        diff_tags = list(set(tags).difference(set(support_test_tags)))
        if len(diff_tags) > 0:
            stdio.error('%s not in test_tags' % ','.join(diff_tags))
            return plugin_context.return_false()
        test_set_by_tag = [test_name(test) for test in find_tag_tests(opt, r"#[ \t]*tags[ \t]*:", tags)]
        if has_test_point:
            test_set = list(set(test_set).intersection(set(test_set_by_tag)))
        else:
            test_set = list(set(test_set_by_tag))
        has_test_point = True
    stdio.verbose('filter mode: {}'.format(opt["filter"]))
    # exclude somt tests.
    if 'exclude' not in opt or not opt['exclude']:
        opt['exclude'] = []
    test_set = filter(lambda k: k not in opt['exclude'], test_set)
    if 'filter' in opt and opt['filter']:
        exclude_test = plugin_context.get_variable('exclude_test')
        exclude_list = exclude_test(opt, stdio)
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
    slb_host = opt.get('slb_host')
    exec_id = opt.get('exec_id')
    use_slb = all([slb_host is not None, exec_id is not None])
    slices = opt.get('slices')
    slice_idx = opt.get('slice_idx')
    use_slices = all([slices is not None, slice_idx is not None])
    if not use_slb and use_slices:
        slices = int(slices)
        slice_idx = int(slice_idx)
        test_set = test_set[slice_idx::slices]
    if 'mode' in opt and opt['mode'] != 'both':
        if opt['mode'] == 'oracle':
            not_run = '_mysql'
            # test_set = filter(lambda k: not k.endswith(not_run), test_set)
            test_set = filter(lambda k: k.endswith('_oracle'), test_set)
        if opt['mode'] == 'mysql':
            not_run = '_oracle'
            test_set = filter(lambda k: not k.endswith(not_run), test_set)
    opt['test_set'] = list(set(test_set))

    if opt.get('reboot_cases'):
        reboot_cases = get_variable_from_python_file(opt['reboot_cases'], var_name='reboot_cases',
                                                 default_file='rebootcases.py', default_value=[], stdio=stdio)
        opt['reboot_cases'] = list(set(test_set).intersection(set(reboot_cases)))
    else:
        opt['reboot_cases'] = []

    if opt['test_set'] is None:
        stdio.error('Test set is empty')
        return plugin_context.return_false()
    return plugin_context.return_true(test_set=test_set)
