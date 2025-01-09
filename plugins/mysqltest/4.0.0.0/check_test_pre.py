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


import os


def check_test_pre(plugin_context, env, *args, **kwargs):
    query_sql = 'select zone, count(*) as a from oceanbase.DBA_OB_ZONES group by region order by a desc limit 1'
    plugin_context.set_variable('query_sql', query_sql)

    def get_variable_from_python_file(file_path, var_name=None, default_file=None, default_value=None, stdio=None):
        global_vars = {}
        try:
            stdio and stdio.verbose('read variable from {}'.format(file_path))
            exec(open(file_path).read(), global_vars, global_vars)
        except Exception as e:
            stdio and stdio.warn(str(e))
            if default_file:
                try:
                    default_path = os.path.join(os.path.dirname(__file__), 'mysqltest_lib', default_file)
                    stdio and stdio.verbose('read variable from {}'.format(file_path))
                    exec(open(default_path).read(), global_vars, global_vars)
                except Exception as ex:
                    stdio and stdio.warn(str(ex))
        if var_name is None:
            return global_vars
        return global_vars.get(var_name, default_value)
    plugin_context.set_variable("get_variable_from_python_file", get_variable_from_python_file)

    def exclude_test(opt, stdio):
        if opt.get('case_filter'):
            filter_dict = get_variable_from_python_file(opt['case_filter'], stdio=stdio)
            var_name = '%s_list' % opt['filter']
            var_ce_name = '%s_ce_list' % opt['filter']
            if not opt['is_business'] and var_ce_name in filter_dict:
                exclude_list = filter_dict[var_ce_name]
            else:
                exclude_list = filter_dict[var_name]
        else:
            exclude_list = []
        return exclude_list

    plugin_context.set_variable("exclude_test", exclude_test)
    return plugin_context.return_true()
