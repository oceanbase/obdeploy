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
from ssh import LocalClient

def check_requirement(plugin_context, file_map=None, requirement_map=None, *args, **kwargs):
    lib_check = False
    need_libs = set()
    java_bin = getattr(plugin_context.options, 'java_bin', 'java')
    cmd = '%s -version' % java_bin
    if not LocalClient.execute_command(cmd, stdio=plugin_context.stdio):
        for file_item in file_map.values():
            need_libs.add(requirement_map[file_item.require])
    return plugin_context.return_true(checked=lib_check, requirements=need_libs)