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

import copy
from tool import get_metadb_info_from_depends_ob, add_http_prefix


def get_general_config(global_config, cluster_config, stdio):
    general_config = {}
    oms_meta_host = None
    oms_meta_port = None
    oms_meta_user = None
    oms_meta_password = None
    ob_metadb_info = get_metadb_info_from_depends_ob(cluster_config, stdio)
    if ob_metadb_info:
        oms_meta_host = ob_metadb_info['host']
        oms_meta_port = str(ob_metadb_info['port'])
        oms_meta_user = ob_metadb_info['user']
        oms_meta_password = ob_metadb_info['password']

    general_config['oms_meta_host'] = global_config.get('oms_meta_host') or oms_meta_host
    general_config['oms_meta_port'] = str(global_config.get('oms_meta_port') or oms_meta_port)
    general_config['oms_meta_user'] = global_config.get('oms_meta_user') or oms_meta_user
    general_config['oms_meta_password'] = global_config.get('oms_meta_password') or oms_meta_password
    general_config['drc_rm_db'] = global_config.get('drc_rm_db', 'oms_rm')
    general_config['drc_cm_db'] = global_config.get('drc_cm_db', 'oms_cm')
    if global_config.get('drc_cm_heartbeat_db'):
        general_config['drc_cm_heartbeat_db'] = global_config.get('drc_cm_heartbeat_db')
    if global_config.get('tsdb_service') == 'INFLUXDB':
        general_config['tsdb_service'] = 'INFLUXDB'
        general_config['tsdb_enabled'] = "true"
        general_config['tsdb_url'] = global_config.get('tsdb_url')
        general_config['tsdb_password'] = global_config.get('tsdb_password')
        general_config['tsdb_username'] = global_config.get('tsdb_username')
    general_config['ghana_server_port'] = str(global_config.get('ghana_server_port'))
    general_config['nginx_server_port'] = str(global_config.get('nginx_server_port'))
    general_config['cm_server_port'] = str(global_config.get('cm_server_port'))
    general_config['supervisor_server_port'] = str(global_config.get('supervisor_server_port'))
    general_config['sshd_server_port'] = str(global_config.get('sshd_server_port'))
    if global_config.get('apsara_audit_sls_access_key'):
        general_config['apsara_audit_sls_access_key'] = global_config.get('apsara_audit_sls_access_key')
        general_config['apsara_audit_sls_access_secret'] = global_config.get('apsara_audit_sls_access_secret')
        general_config['apsara_audit_sls_endpoint'] = global_config.get('apsara_audit_sls_endpoint')
        general_config['apsara_audit_sls_ops_site_topic'] = global_config.get('apsara_audit_sls_ops_site_topic')
        general_config['apsara_audit_sls_user_site_topic'] = global_config.get('apsara_audit_sls_user_site_topic')
    return general_config


class Region(object):
    def __init__(self, data):
        self.region_data = {}
        self.load_data(data)
        self.parameters_check()

    def __getitem__(self, item):
        return self.region_data[item]

    def get(self, key, default=None):
        return self.region_data.get(key, default)

    def load_data(self, data):
        if isinstance(data, dict):
            self.region_data = data
        else:
            raise TypeError('region data must be dict.')

    def parameters_check(self):
        if not self.region_data.get('cm_url'):
            raise ValueError('cm_url is required.')
        if self.region_data.get('cm_location', None) is None:
            raise ValueError('cm_location is required.')
        if not self.region_data.get('cm_nodes'):
            raise ValueError('cm_nodes is required.')
        if self.region_data.get('cm_is_default', None) is None:
            raise ValueError('cm_is_default is required.')
def bool_to_str(value):
    return "true" if value else "false"


def generate_oms_config(plugin_context, new_cluster_config=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    if new_cluster_config:
        cluster_config = new_cluster_config
    global_config = cluster_config.get_global_conf_with_default()
    general_config = get_general_config(global_config, cluster_config, stdio)

    if "@sys" in global_config.get('oms_meta_user', ""):
        stdio.error("The oms_meta_user cannot support `@sys`")
        return plugin_context.return_false()
    regions = global_config.get('regions', [])
    regions_config = {}
    regions_server_map = {}
    default_region = None
    regions_ip_count = 0
    for region_dict in regions:
        try:
            region = Region(region_dict)
        except Exception as e:
            stdio.error('region data error: %s' % str(e))
            return plugin_context.return_false()
        regions_server_map[region] = []
        servers = regions_server_map[region]
        drc_cm_heartbeat_dbs = []
        cm_locations = []
        regions_config[region] = copy.deepcopy(general_config)
        config = regions_config[region]
        settings = global_config.get('settings', {})
        for key, value in settings.items():
            if key not in config:
                config[key] = value
        config['cm_url'] = add_http_prefix(region['cm_url'])
        if len(config['cm_url'].split(':')) == 1:
            cm_url_port = '80'
        else:
            cm_url_port = config['cm_url'].split(':')[1]
        if str(cm_url_port) != str(config['cm_server_port']):
            stdio.warn('If the cm_url is not VIP configured, keep the port consistent with cm_server_port.')

        cm_location = str(region['cm_location'])
        if cm_location not in cm_locations:
            cm_locations.append(cm_location)
        else:
            stdio.error('Duplicate cm_location: %s' % cm_location)
            return plugin_context.return_false()
        config['cm_location'] = region['cm_location']
        if len(regions) > 1:
            config['cm_region'] = region['cm_region']
            config['cm_region_cn'] = region.get('cm_region_cn') or region['cm_region']
        if region['cm_is_default']:
            if default_region:
                stdio.error('Only one region can be default.')
                return plugin_context.return_false()
            else:
                default_region = region
        config['cm_is_default'] = bool_to_str(region['cm_is_default'] or False)
        config['cm_nodes'] = region['cm_nodes']
        regions_ip_count += len(region['cm_nodes'])
        for ip in region['cm_nodes']:
            for server in cluster_config.servers:
                if ip == server.ip:
                    servers.append(server)
        drc_cm_heartbeat_db = region.get('drc_cm_heartbeat_db') or (global_config.get('drc_cm_heartbeat_db', 'oms_cm_heartbeat') + "_" + str(region['cm_location']))
        if drc_cm_heartbeat_db not in drc_cm_heartbeat_dbs:
            drc_cm_heartbeat_dbs.append(drc_cm_heartbeat_db)
        else:
            stdio.error('Duplicate drc_cm_heartbeat_db: %s' % drc_cm_heartbeat_db)
            return plugin_context.return_false()
        config['drc_cm_heartbeat_db'] = drc_cm_heartbeat_db

    if default_region is None:
        stdio.error("There is only one region, which `cm_is_default` in needs to be set to true")
        return plugin_context.return_false()

    if regions_ip_count != len(cluster_config.servers):
        stdio.error('The number of servers in the region is not equal to the number of servers in the cluster.')
        return plugin_context.return_false()

    plugin_context.set_variable('regions_server_map', regions_server_map)
    plugin_context.set_variable('regions_config', regions_config)

    return plugin_context.return_true()
