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


def restart_pre(plugin_context, *args, **kwargs):
    plugin_context.set_variable('clients', plugin_context.clients)
    plugin_context.set_variable('dir_list', ['home_path'])
    plugin_context.set_variable('finally_plugins', ['connect', 'display'])
    plugin_context.set_variable('need_bootstrap', False)
    return plugin_context.return_true()



