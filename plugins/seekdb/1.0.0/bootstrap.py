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

import time

from _deploy import InnerConfigItem


def bootstrap(plugin_context, *args, **kwargs):
    need_bootstrap = plugin_context.get_variable('need_bootstrap')
    if not need_bootstrap:
        return plugin_context.return_true()
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('connect').get_return('cursor')
    global_conf = cluster_config.get_global_conf()
    raise_cursor = cursor.raise_cursor

    if global_conf.get('root_password') is not None:
        sql = 'alter user "root" IDENTIFIED BY %s'
        raise_cursor.execute(sql, [global_conf.get('root_password')])
        cursor.password = global_conf.get('root_password')
    stdio.stop_loading('succeed')

    return plugin_context.return_true()
