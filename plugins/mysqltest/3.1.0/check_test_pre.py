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

import os
from const import COMP_OB_SEEKDB


def check_test_pre(plugin_context, env, *args, **kwargs):
    repository = kwargs.get("repository")
    if repository.name != COMP_OB_SEEKDB:
        query_sql = 'select zone, count(*) as a from oceanbase.__all_virtual_zone_stat group by region order by a desc limit 1'
        plugin_context.set_variable('query_sql', query_sql)

    def get_variable_from_python_file(file_path, var_name, default_file=None, default_value=None, stdio=None):
        global_vars = {}
        try:
            stdio and stdio.verbose('read variable {} from {}'.format(var_name, file_path))
            exec(open(file_path).read(), global_vars, global_vars)
        except Exception as e:
            stdio and stdio.warn(str(e))
            if default_file:
                try:
                    default_path = os.path.join(os.path.dirname(__file__), 'mysqltest_lib', default_file)
                    stdio and stdio.verbose('read variable {} from {}'.format(var_name, file_path))
                    exec(open(default_path).read(), global_vars, global_vars)
                except Exception as ex:
                    stdio and stdio.warn(str(ex))
        return global_vars.get(var_name, default_value)
    plugin_context.set_variable("get_variable_from_python_file", get_variable_from_python_file)

    def exclude_test(opt, stdio):
        if opt.get('case_filter'):
            exclude_list = get_variable_from_python_file(opt['case_filter'], var_name='%s_list' % opt['filter'],
                                                         default_file='case_filter.py', default_value=[], stdio=stdio)
        else:
            exclude_list = []
        return exclude_list
    plugin_context.set_variable("exclude_test", exclude_test)

    return plugin_context.return_true()
