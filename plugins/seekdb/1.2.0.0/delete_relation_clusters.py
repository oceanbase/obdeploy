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

def delete_cluster_standby_relation_in_inner_config(cluster_config, cluster_config_deleted, stdio):
    relation_dict = cluster_config.get_component_attr('_cluster_standby_relation')
    if relation_dict:
        if cluster_config_deleted in relation_dict:
            relation_dict.remove(cluster_config_deleted)
        cluster_config.update_component_attr('_cluster_standby_relation', relation_dict if relation_dict else {}, save=True)


def delete_relation_clusters(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    stdio = plugin_context.stdio
    standby_deploy_name = plugin_context.cluster_config.deploy_name

    deploy_conf = cluster_configs.get(standby_deploy_name)
    option_type = kwargs.get('option_type')

    # Failover/decouple: only sever link to my primary; keep my own standbys
    # Destroy: remove all relations including my standbys (no option_type passed).
    is_failover_or_decouple = (option_type in ['failover', 'decouple'])

    primary_deploy_name = deploy_conf.get_component_attr('_cluster_primary')
    stdio.start_loading("Delete the relationship related to %s" % standby_deploy_name)

    if primary_deploy_name:
        stdio.verbose("Removing primary cluster relation: {}.".format(primary_deploy_name))
        primary_cluster_config = cluster_configs.get(primary_deploy_name)
        if option_type in ['failover', 'decouple']:
            standby_cursor = cursors.get(standby_deploy_name)
            sql = 'select log_restore_source from oceanbase.__all_virtual_server_stat'
            res = standby_cursor.fetchone(sql, stdio=stdio)
            if not res:
                stdio.error("%s get primary log_restore_source failed" % standby_deploy_name)
                stdio.stop_loading('fail')
                return plugin_context.return_false()

            service_str = ""
            if primary_cluster_config:
                primary_server = primary_cluster_config.servers[0]
                primary_server_conf = primary_cluster_config.get_server_conf_with_default(primary_server)
                service_str = "%s:%s" % (primary_server.ip, primary_server_conf.get('rpc_port'))
            if res['log_restore_source'] != service_str:
                stdio.error(
                    "ip and rpc_port mismatch when decoupling/failover: expected %s, got %s."
                    % (res.get('log_restore_source'))
                )
                stdio.stop_loading('fail')
                return plugin_context.return_false()

        if primary_cluster_config:
            delete_cluster_standby_relation_in_inner_config(primary_cluster_config, standby_deploy_name, stdio)
    deploy_conf.update_component_attr('_cluster_primary', None, save=True)

    # Only clear my standbys when destroying the cluster, not when failover/decouple.
    if not is_failover_or_decouple:
        standby_relations = deploy_conf.get_component_attr('_cluster_standby_relation')
        if standby_relations:
            for standby_name in standby_relations:
                stdio.verbose("Removing primary relation from standby cluster: {}.".format(standby_name))
                standby_conf = cluster_configs.get(standby_name)
                if standby_conf:
                    standby_conf.update_component_attr('_cluster_primary', None, save=True)
            deploy_conf.update_component_attr('_cluster_standby_relation', None, save=True)

    stdio.verbose("Deleted cluster relations in inner_config.yaml.")
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
