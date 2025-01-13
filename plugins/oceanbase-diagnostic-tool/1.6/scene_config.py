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

