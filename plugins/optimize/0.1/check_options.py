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


def check_options(plugin_context, *args, **kwargs):

    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

    stdio = plugin_context.stdio
    options = plugin_context.options
    optimize_config = kwargs.get('optimize_config')

    sql_file_pattern = r'^optimize_(oceanbase|oceanbase_ce|obproxy|obproxy_ce)_stage_(\w+)_sql_file(_by_sys)?$'
    for key in vars(options):
        matched = re.match(sql_file_pattern, key)
        if matched:
            component = matched.group(1).replace('_', '-')
            stage = matched.group(2)
            exec_by_sys = bool(matched.group(3))
            path = get_option(key)
            stdio.verbose('execute sql file {}{} when optimizing the component {} in stage {}'.format(path, 'by sys' if exec_by_sys else '', component, stage))
            optimize_config.set_exec_sql(component=component, stage=stage, sql_kwargs_list=[{'path': path, 'sys': exec_by_sys}])
    return plugin_context.return_true()