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


def init_pre(plugin_context, *args, **kwargs):
    kill_cmd = "pkill -9 -u `whoami` -f '^%s/bin/monagent -c conf/monagent.yaml'"
    mkdir_keys = "bash -c 'mkdir -p %s/{run,bin,lib,conf,log}'"
    plugin_context.set_variable('kill_cmd', kill_cmd)
    plugin_context.set_variable('mkdir_keys', mkdir_keys)
    return plugin_context.return_true()