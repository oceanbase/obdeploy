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

from tool import Cursor


def register_configserver(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    stdio = plugin_context.stdio
    stdio.start_loading('%s register ob-configserver' % cluster_config.name)
    cfg_url = plugin_context.get_variable('cfg_url')

    if not cfg_url or 'ob-configserver' not in added_components:
        stdio.error('Failed to register obconfig_url')
        return plugin_context.return_false()

    for comp in ["oceanbase-ce", "oceanbase"]:
        if comp in added_components:
            stdio.error('Failed to register obconfig_url')
            return plugin_context.return_false()

    cursor = plugin_context.get_return('connect').get_return('cursor')
    try:
        cursor.execute("alter system set obconfig_url = '%s'" % cfg_url)
        cursor.execute("alter system reload server")
    except:
        stdio.error('Failed to register obconfig_url')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()


