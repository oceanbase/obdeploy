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
import const

def load_mysqltest_snap(plugin_context, workflow, repository, *args, **kwargs):
    env = plugin_context.namespace.get_variable("env")
    snap_configs = kwargs.get('snap_configs')
    home_path = os.path.join(os.environ.get(const.CONST_OBD_HOME, os.getenv('HOME')), '.obd')

    workflow.add_with_component_version(const.STAGE_FIRST, repository.name, repository.version, 'stop')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', "0.1", {"env": env, "snap_config": snap_configs[repository], "repository": repository}, 'load_snap')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, repository.name, repository.version, {"home_path": home_path}, 'start')
    return plugin_context.return_true()