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
import os
from ssh import LocalClient

def scene_config(plugin_context, *args, **kwargs):

    def get_option(key, default=''):
        value = getattr(options, key)
        if value is None:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value

    def check_config():
        home = os.path.expanduser("~")
        base_path = os.path.join(home, ".obdiag")
        required = {
            "check": {"tasks": True},
            "example": True,
            "gather": {"tasks": True}
        }
        for item, content in required.items():
            full_path = os.path.join(base_path, item)
            if isinstance(content, dict):
                if not os.path.isdir(full_path):
                    return False
                for sub_item, is_dir in content.items():
                    sub_full_path = os.path.join(full_path, sub_item)
                    if is_dir:
                        if not os.path.isdir(sub_full_path):
                            return False
                    else:
                        if not os.path.isfile(sub_full_path):
                            return False
            else:
                if content:
                    if not os.path.isdir(full_path):
                        return False
                else:
                    if not os.path.isfile(full_path):
                        return False
        return True

    def init():
        obdiag_install_dir = get_option('obdiag_dir')
        init_shell_path = os.path.join(obdiag_install_dir, 'init.sh')
        init_command = 'sh {0}'.format(init_shell_path)
        if LocalClient.execute_command(init_command, None, None, None):
            return True
        else:
            stdio.error("excute command: {0} failed".format(init_command))
            return False

    stdio = plugin_context.stdio
    options = plugin_context.options
    if check_config():
        init_status = True 
    else:
        init_status = init()
    if init_status:
        return plugin_context.return_true()
    else:
        return plugin_context.return_false()

