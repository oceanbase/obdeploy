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
    be_depend = cluster_config.be_depends
    plugins = []
    if 'obagent' in added_components and 'obagent' in be_depend:
        add_plugin('generate_config', plugins)
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
    if ('obproxy-ce' in added_components and 'obproxy-ce' in be_depend or 'obproxy' in added_components and 'obproxy' in be_depend):
        add_plugin('generate_config', plugins)
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
    if 'ocp-express' in added_components and 'ocp-express' in be_depend:
        add_plugin('generate_config', plugins)
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
        add_plugin('create_tenant', plugins)
    if 'ob-configserver' in added_components:
        cluster_config.add_depend_component('ob-configserver')
        
    plugin_context.stdio.verbose('scale_out_check plugins: %s' % plugins)
    plugin_context.stdio.verbose('added_components: %s' % added_components)
    return plugin_context.return_true(plugins=plugins)
