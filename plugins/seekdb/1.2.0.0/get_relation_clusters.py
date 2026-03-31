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
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

def get_relation_clusters(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    deploy_manager = kwargs.get('deploy_manager')
    # Use the current deploy name as start
    deploy_name = plugin_context.cluster_config.deploy_name
    
    queue = Queue()
    queue.put(deploy_name)
    visited = set()
    relation_deploy_names = set()
    cluster_configs = {}

    while not queue.empty():
        curr_name = queue.get()
        if curr_name in visited:
            continue
        visited.add(curr_name)
        
        deploy = deploy_manager.get_deploy_config(curr_name)
        if not deploy:
            stdio.verbose('No such deploy: %s.' % curr_name)
            continue
            
        # Get seekdb component
        cluster_config = deploy.deploy_config.components.get('seekdb')
        if not cluster_config:
            stdio.verbose('No seekdb component in: %s.' % curr_name)
            continue
            
        cluster_configs[curr_name] = cluster_config
        relation_deploy_names.add(curr_name)
        
        # Get relations
        # _cluster_standby_relation is a list of standby names
        standbys = cluster_config.get_component_attr('_cluster_standby_relation') or []
        # _cluster_primary is a single name
        primary = cluster_config.get_component_attr('_cluster_primary')
        
        if primary and primary not in visited:
            queue.put(primary)
            
        for sb in standbys:
            if sb not in visited:
                queue.put(sb)
                
    plugin_context.set_variable('relation_deploy_names', list(relation_deploy_names))
    plugin_context.set_variable('cluster_configs', cluster_configs)
    return plugin_context.return_true()
