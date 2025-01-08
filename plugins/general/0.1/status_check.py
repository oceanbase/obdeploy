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

from _deploy import ClusterStatus


def status_check(plugin_context, target_status=ClusterStatus.STATUS_RUNNING, is_error=False, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    cluster_status = plugin_context.get_return('status').get_return('cluster_status')
    print_msg = stdio.error if is_error else stdio.warn
    status_msg = 'running' if target_status == ClusterStatus.STATUS_RUNNING else 'stopped'
    status_check_pass = True
    for server in cluster_status:
        if cluster_status[server] != target_status.value:
            status_check_pass = False
            print_msg("%s %s is not %s" % (server, cluster_config.name, status_msg))

    if status_check_pass:
        return plugin_context.return_true(status_check_pass=status_check_pass)
    return plugin_context.return_false(status_check_pass=status_check_pass)
