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


def upload_packages(plugin_context, cursor, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    ob_with_opti_pkgs = plugin_context.get_variable('ob_with_opti_pkgs', default=[])
    for server in servers:
        api_cursor = cursor.get(server)
        for pkg in ob_with_opti_pkgs:
            stdio.verbose('upload package %s' % pkg.file_name)
            if not api_cursor.upload_packages(files={'file': open(pkg.path, 'rb')}, stdio=stdio):
                stdio.error('upload package %s failed' % pkg.file_name)
                continue
        break
    return plugin_context.return_true()
