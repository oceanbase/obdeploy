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


def add_plugin(component_name, plugins):
    if component_name not in plugins:
        plugins.append(component_name)


def scale_out_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    plugins = []
    plugin_context.set_variable('need_bootstrap', False)
    need_restart = False
    if 'ob-configserver' in added_components:
        cluster_config.add_depend_component('ob-configserver')

    if 'obproxy-ce' in added_components or 'obproxy' in added_components:
        plugin_context.set_variable('auto_depend', True)
        add_plugin('generate_config', plugins)

    if 'ob-configserver' in added_components and 'obproxy-ce' not in added_components and 'obproxy' not in added_components:
        need_restart = True

    plugin_context.stdio.verbose('scale_out_check plugins: %s' % plugins)
    plugin_context.stdio.verbose('added_components: %s' % added_components)
    return plugin_context.return_true(plugins=plugins, need_restart=need_restart)
