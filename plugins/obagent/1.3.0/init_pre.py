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


def init_pre(plugin_context, *args, **kwargs):
    kill_cmd = "%s/bin/ob_agentctl stop"
    mkdir_keys = "bash -c 'mkdir -p %s/{run,bin,conf,log,tmp,backup,pkg_store,task_store,position_store,site-packages}'"
    plugin_context.set_variable('kill_cmd', kill_cmd)
    plugin_context.set_variable('mkdir_keys', mkdir_keys)
    return plugin_context.return_true()