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


def upgrade_version(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading('upgrade init')
    cursor = plugin_context.get_variable('cursor')
    version = plugin_context.get_variable('cur_version')
    try:
        version_list = [int(_i) for _i, _s in re.findall('(\d+)([^\._]*)', version)]

        sql = """
        CREATE TABLE IF NOT EXISTS `oms_version` (    
       `version` varchar(64) NOT NULL COMMENT '版本',    
       `gmt_modified` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,    
       PRIMARY KEY (`version`)
       ) DEFAULT CHARSET = utf8mb4 COMMENT = '版本表';
    
        REPLACE INTO `oms_version`(`version`) VALUES('%s.%s.%s-CE');
        """ % (version_list[0], version_list[1], version_list[2])

        cursor.execute(sql)
    except Exception as e:
        stdio.error("offline upgrade failed, error: %s" % str(e))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()







