# coding: utf-8
from __future__ import absolute_import, division, print_function

class ClusterNode:
    def __init__(self, name):
        self.name = name
        self.primary = None
        self.standbys = []

site = []

def generate_file_tree_global(node, depth, stdio):
    global site
    nodes_list = node.standbys
    if len(nodes_list) < 1:
        return

    if not node.primary:
        stdio.print(node.name)
    
    # Sort standbys for consistent output
    nodes_list.sort(key=lambda x: x.name)
    last_node = nodes_list[-1]
    
    for sub_node in nodes_list:
        string_list = ["│   " for _ in range(depth - len(site))]
        for s in site:
            string_list.insert(s, "    ")

        if sub_node != last_node:
            string_list.append("├── ")
        else:
            string_list.append("└── ")
            site.append(depth)

        stdio.print("".join(string_list) + sub_node.name)
        if sub_node.standbys:
            generate_file_tree_global(sub_node, depth + 1, stdio)
        if sub_node == last_node:
            site.pop()

def show_topology(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
    
    if not getattr(options, 'graph', False):
        return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    deploy_manager = kwargs.get('deploy_manager')
    
    # BFS to find all related clusters
    visited = set()
    queue = [cluster_config.deploy_name]
    nodes = {} # name -> ClusterNode
    
    # Initialize current node
    nodes[cluster_config.deploy_name] = ClusterNode(cluster_config.deploy_name)

    while queue:
        curr_name = queue.pop(0)
        if curr_name in visited:
            continue
        visited.add(curr_name)
        
        deploy = deploy_manager.get_deploy_config(curr_name)
        if not deploy:
            continue
        
        comp = deploy.deploy_config.components.get('seekdb')
        if not comp:
            continue
            
        if curr_name not in nodes:
            nodes[curr_name] = ClusterNode(curr_name)
        
        node = nodes[curr_name]
        
        # Get relations
        relations = comp.get_component_attr('_cluster_standby_relation') or []
        primary_name = comp.get_component_attr('_cluster_primary')
        
        # Link Primary
        if primary_name:
            if primary_name not in nodes:
                nodes[primary_name] = ClusterNode(primary_name)
            primary_node = nodes[primary_name]
            node.primary = primary_node
            
            # Link Standby (avoid duplicates)
            if node not in primary_node.standbys:
                primary_node.standbys.append(node)
            
            # Add primary to queue
            if primary_name not in visited:
                queue.append(primary_name)

        # Add other relations to queue
        for r_name in relations:
            if r_name not in visited:
                queue.append(r_name)

    if len(nodes) <= 1:
        return plugin_context.return_true()

    stdio.print('\nCluster Topology:\n')
    
    # Sort nodes for consistent printing order
    # Find all root nodes (nodes without primary)
    root_nodes = [node for node in nodes.values() if not node.primary]
    
    # Sort roots by name
    root_nodes.sort(key=lambda x: x.name)
    
    has_printed = False
    for node in root_nodes:
        # Reset site for each tree
        global site
        site = []
        
        generate_file_tree_global(node, 0, stdio)
        stdio.print('')
        has_printed = True

    if not has_printed and nodes:
        # Fallback for single node or weird state
        stdio.print(cluster_config.deploy_name)
    
    return plugin_context.return_true()
