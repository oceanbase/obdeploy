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

from tool import ConfigUtil


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    if cluster_config.name in add_components and 'admin_passwd' not in global_config:
        cluster_config.update_global_conf('admin_passwd', ConfigUtil.get_random_pwd_by_rule(), False)
    cluster_config.update_global_conf('ocp_root_password', ConfigUtil.get_random_pwd_by_rule(), False)


def generate_config_pre(plugin_context, *args, **kwargs):
    generate_keys = ['admin_passwd']
    plugin_context.set_variable('generate_keys', generate_keys)
    plugin_context.set_variable('generate_random_password', generate_random_password)
    return plugin_context.return_true()