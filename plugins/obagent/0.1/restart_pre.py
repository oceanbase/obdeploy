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

from tool import set_plugin_context_variables


def restart_pre(plugin_context, *args, **kwargs):
    new_clients = kwargs.get('new_clients')
    new_deploy_config = kwargs.get('new_deploy_config')
    variables_dict = {
        "clients": plugin_context.clients,
        "dir_list": ['home_path'],
        "finally_plugins": ['display'],
        "need_bootstrap": False,
        "new_clients": new_clients,
        "new_deploy_config": new_deploy_config
    }
    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()



