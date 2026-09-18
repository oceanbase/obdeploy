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
from pymysql import err
from _deploy import ObserverIdentity, ObserverIdentityError


def get_deployment_connections(plugin_context, relation_deploy_names=None, cursors=None, cluster_configs=None, retry_times=1, not_connect_act="ignore", *args, **kwargs):
    relation_deploy_names = [] if relation_deploy_names is None else relation_deploy_names
    cursors = {} if cursors is None else cursors
    cluster_configs = {} if cluster_configs is None else cluster_configs
    def call_plugin(plugin, cluster_config, *args, **kwargs):
        return plugin(plugin_context.namespace, plugin_context.namespaces, plugin_context.deploy_name, plugin_context.deploy_status,
            plugin_context.repositories, plugin_context.components, plugin_context.clients,
            cluster_config, plugin_context.cmds, plugin_context.options,
            None, *args, **kwargs)

    stdio = plugin_context.stdio
    stdio.start_loading('Get deployment connections')
    if not_connect_act not in ["ignore", "raise"]:
        stdio.error(err.EC_INVALID_PARAMETER.format('not_connect_act', not_connect_act))
    deploy_name = plugin_context.cluster_config.deploy_name
    cmds = plugin_context.cmds
    if kwargs.get('option_mode') == 'create_standby_tenant':
        relation_deploy_names = [cmds[1], cmds[0]]
    if deploy_name not in relation_deploy_names:
        relation_deploy_names.append(deploy_name)
    cluster_configs[plugin_context.cluster_config.deploy_name] = plugin_context.cluster_config
    protected_modes = {
        'log_source'
    }
    if kwargs.get('option_mode') in protected_modes:
        try:
            ObserverIdentity.reject_loopback_capability(cluster_configs, kwargs.get('option_mode'))
        except ObserverIdentityError as e:
            stdio.error(str(e))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
    verified_loopback_modes = {
        'create_standby_tenant', 'switchover_tenant', 'switchover',
        'failover_decouple_tenant', 'set_sync_mode'
    }
    if kwargs.get('option_mode') in verified_loopback_modes:
        try:
            ObserverIdentity.require_verified_loopback_capability(
                cluster_configs, kwargs.get('option_mode'))
        except ObserverIdentityError as e:
            stdio.error(str(e))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
    plugin_manager = kwargs.get('plugin_manager')
    repository = kwargs.get('repository')
    connect_plugin = plugin_manager.get_best_py_script_plugin('connect', repository.name, repository.version)
    for deploy_name in relation_deploy_names:
        if not cursors.get(deploy_name):
            cluster_config = cluster_configs[deploy_name]
            ret = call_plugin(connect_plugin, cluster_config, retry_times=retry_times)
            if ret:
                cursor = ret.get_return('cursor')
                if cursor.execute('show databases', raise_exception=False, exc_level='info'):
                    # set stdio for cursor ,because call plugin to set stdio is None for no error occurs
                    cursor.stdio = stdio
                    cursors[deploy_name] = cursor
                    continue
                stdio.verbose("{}'s observer connection unavailable.".format(deploy_name))  
            if not_connect_act == "ignore":
                continue
            else:
                # If entering this branch requires an error code to be filled.
                stdio.error("{}'s observer connection fail.".format(deploy_name))
                stdio.stop_loading('fail')
                return plugin_context.return_false()
    if kwargs.get('option_mode') in verified_loopback_modes:
        try:
            if kwargs.get('option_mode') == 'create_standby_tenant':
                missing_connections = [
                    name for name in relation_deploy_names if not cursors.get(name)]
                if missing_connections:
                    raise ObserverIdentityError(
                        '%s requires connections to deployments: %s' % (
                            kwargs.get('option_mode'), ', '.join(missing_connections)))
            for relation_deploy_name, cluster_config in cluster_configs.items():
                ObserverIdentity.require_verified_observed_loopback_capability(
                    cluster_config, cursors.get(relation_deploy_name), kwargs.get('option_mode'))
        except ObserverIdentityError as e:
            stdio.error(str(e))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
    stdio.stop_loading('succeed')
    plugin_context.set_variable('cursors', cursors)
    return plugin_context.return_true()
