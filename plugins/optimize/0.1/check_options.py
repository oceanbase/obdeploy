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