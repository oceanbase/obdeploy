# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function

import re
from copy import deepcopy
from collections import OrderedDict

from tool import ConfigUtil
from _deploy import (
    InnerConfigItem, 
    ServerConfigFlyweightFactory, 
    ClusterConfig, 
    ConfigParser,
    CommentedMap,
    RsyncConfig,
    ENV
)


class ClusterConfigParser(ConfigParser):

    STYLE = 'cluster'
    INNER_CONFIG_MAP = {
        '$_zone_idc': 'idc'
    }
    META_KEYS = ['version', 'tag', 'release', 'package_hash', 'config', RsyncConfig.RSYNC, ENV]

    @classmethod
    def get_server_src_conf(cls, cluster_config, component_config, server):
        server_config = cluster_config.get_server_conf(server)
        zones = component_config['zones']
        zone_name = server_config.get('zone', list(zones.keys())[0])
        zone = zones[zone_name]
        if 'config' not in zone:
            zone['config'] = {}
        zone_config = zone['config']
        if server.name not in zone_config:
            zone_config[server.name] = {}
        return zone_config[server.name]

    @classmethod
    def get_global_src_conf(cls, cluster_config, component_config):
        if 'config' not in component_config:
            component_config['config'] = {}
        return component_config['config']

    @classmethod
    def _to_cluster_config(cls, component_name, conf, added_servers=None):
        servers = OrderedDict()
        zones = conf.get('zones', {})
        for zone_name in zones:
            zone = zones[zone_name]
            zone_servers = cls._get_servers(zone.get('servers', []))
            zone_configs = zone.get('config', {})
            zone_global_config = zone_configs.get('global', {})
            for server in zone_servers:
                if server not in servers:
                    server_config = deepcopy(zone_global_config)
                    if server.name in zone_configs:
                        server_config.update(zone_configs[server.name])
                    if 'idc' in zone:
                        key = '$_zone_idc'
                        if key in server_config:
                            del server_config[key]
                        server_config[InnerConfigItem(key)] = str(zone['idc'])
                    server_config['zone'] = zone_name
                    servers[server] = server_config

        cluster_config = ClusterConfig(
            servers.keys(),
            component_name,
            ConfigUtil.get_value_from_dict(conf, 'version', None, str),
            ConfigUtil.get_value_from_dict(conf, 'tag', None, str),
            ConfigUtil.get_value_from_dict(conf, 'release', None, str),
            ConfigUtil.get_value_from_dict(conf, 'package_hash', None, str)
        )
        if added_servers:
            cluster_config.added_servers = added_servers
        global_config = {}
        if 'id' in conf:
            global_config['cluster_id'] = int(conf['id'])
        if 'name' in conf:
            global_config['appname'] = str(conf['name'])
        if 'config' in conf:
            global_config.update(conf['config'])
        cluster_config.set_global_conf(global_config)

        if RsyncConfig.RSYNC in conf:
            cluster_config.set_rsync_list(conf[RsyncConfig.RSYNC])

        if ENV in conf:
            cluster_config.set_environments(conf[ENV])

        for server in servers:
            cluster_config.add_server_conf(server, servers[server])
        return cluster_config

    @classmethod
    def merge_config(cls, component_name, config, new_config):
        unmergeable_keys = cls.META_KEYS + ['config', RsyncConfig.RSYNC, ENV]
        for key in unmergeable_keys:
            assert key not in new_config, Exception('{} is not allowed to be set in additional conf'.format(key))
        zones = config.get('zones', {})
        merge_zones = new_config.get('zones', {})
        all_servers = []
        added_servers = []
        for zone in zones.values():
            all_servers.extend(cls._get_servers(zone.get('servers', [])))

        for zone_name in merge_zones:
            exists_zone = zone_name in zones
            merge_zone = merge_zones[zone_name]
            merge_config = merge_zone.get('config', {})
            merge_servers_data = merge_zone.get('servers', [])
            merge_servers = cls._get_servers(merge_servers_data)
            for server in merge_servers:
                assert server not in all_servers, Exception('Server {} is already in cluster'.format(server))
            merge_server_names = [s.name for s in merge_servers]
            added_servers.extend(merge_servers)
            for key in merge_config:
                assert key == 'global' or key in merge_server_names, Exception("{} is not allowed to be set in {}'s config".format(key, zone_name))
            if exists_zone:
                zone = zones[zone_name]
                zone_servers_data = zone.get('servers', [])
                zone_config = zone.get('config', {})
                assert 'idc' not in merge_zone or merge_zone['idc'] == zone.get('idc'), Exception('idc is not allowed to be changed in {}'.format(zone_name))
                for key in merge_config:
                    assert key in merge_server_names, Exception('{} is not allowed to be set in {}.'.format(key, zone_name))
                zone_servers_data.extend(merge_servers_data)
                zone['servers'] = zone_servers_data
                for key in merge_config:
                    zone_config[key] = merge_config[key]
                zone['config'] = zone_config
            else:
                zones[zone_name] = merge_zone
        config['zones'] = zones
        return cls.to_cluster_config(component_name, config, added_servers)

    @classmethod
    def extract_inner_config(cls, cluster_config, config):
        inner_config = cluster_config.get_inner_config()
        for server in inner_config:
            server_config = inner_config[server]
            keys = list(server_config.keys())
            for key in keys:
                if key in cls.INNER_CONFIG_MAP:
                    del server_config[key]

        for server in cluster_config.servers:
            if server.name not in inner_config:
                inner_config[server.name] = {}
            server_config = cluster_config.get_server_conf(server)
            keys = list(server_config.keys())
            for key in keys:
                if cls._is_inner_item(key) and key not in cls.INNER_CONFIG_MAP:
                    inner_config[server.name] = server_config[key]
                    del server_config[key]
        return inner_config

    @classmethod
    def _from_cluster_config(cls, conf, cluster_config):
        global_config_items = {}
        zones_config = {}
        zones = CommentedMap()
        for server in cluster_config.servers:
            server_config = cluster_config.get_server_conf(server)
            server_config_with_default = cluster_config.get_server_conf_with_default(server)
            zone_name = server_config_with_default.get('zone', 'zone1')
            if zone_name not in zones:
                zones[zone_name] = CommentedMap()
            if zone_name not in zones_config:
                zones_config[zone_name] = {
                    'servers': OrderedDict(),
                    'config': OrderedDict(),
                }
            zone_servers = zones_config[zone_name]['servers']
            zone_config_items = zones_config[zone_name]['config']
            zone_servers[server] = server_config
            for key in server_config:
                if cls._is_inner_item(key):
                    if key in cls.INNER_CONFIG_MAP:
                        if cls.INNER_CONFIG_MAP[key] in zones[zone_name]:
                            assert zones[zone_name][cls.INNER_CONFIG_MAP[key]] == server_config[key], Exception('key {} in zone {} is inconsistent '.format(cls.INNER_CONFIG_MAP[key], zone_name))
                        else:
                            zones[zone_name][cls.INNER_CONFIG_MAP[key]] = server_config[key]
                    continue
                if key in zone_config_items:
                    if zone_config_items[key]['value'] == server_config[key]:
                        zone_config_items[key]['count'] += 1
                else:
                    zone_config_items[key] = {
                        'value': server_config[key],
                        'count': 1
                    }

        for zone_name in zones_config:
            zone_global_config = {}
            zone_servers = zones_config[zone_name]['servers']
            zone_config_items = zones_config[zone_name]['config']
            zone_server_num = len(zone_servers)
            zone_global_config_items = {}
            for key in zone_config_items:
                item = zone_config_items[key]
                clear_item = isinstance(key, InnerConfigItem)
                if item['count'] == zone_server_num:
                    zone_global_config_items[key] = item['value']
                    if key in global_config_items:
                        if global_config_items[key]['value'] == zone_global_config_items[key]:
                            global_config_items[key]['count'] += 1
                    else:
                        global_config_items[key] = {
                            'value': zone_global_config_items[key],
                            'count': 1
                        }
                    clear_item = True

                if clear_item:
                    for server in zone_servers:
                        del zone_servers[server][key]
                        
            for key in zone_global_config_items:
                if cls._is_inner_item(key):
                    if key in cls.INNER_CONFIG_MAP:
                        zones[zone_name][cls.INNER_CONFIG_MAP[key]] = zone_global_config_items[key]
                else:
                    zone_global_config[key] = zone_global_config_items[key]

            zones[zone_name]['servers'] = []
            zone_config = {}
            
            if 'zone' in zone_global_config:
                del zone_global_config['zone']
            if zone_global_config:
                zone_config['global'] = zone_global_config

            for server in zone_servers:
                if server.name == server.ip:
                    zones[zone_name]['servers'].append(server.name)
                else:
                    zones[zone_name]['servers'].append({'name': server.name, 'ip': server.ip})
                if zone_servers[server]:
                    zone_config[server.name] = zone_servers[server]
            if zone_config:
                zones[zone_name]['config'] = zone_config
        
        global_config = CommentedMap()
        zone_num = len(zones)
        del global_config_items['zone']
        for key in global_config_items:
            item = global_config_items[key]
            if item['count'] == zone_num:
                global_config[key] = item['value']
                for zone_name in zones:
                    del zones[zone_name]['config']['global'][key]
        
        for zone_name in zones:
            if 'config' in zones[zone_name]:
                configs = zones[zone_name]['config']
                keys = list(configs.keys())
                for key in keys:
                    if not configs[key]:
                        del configs[key]
                if not configs:
                    del zones[zone_name]['config']
                

        if 'cluster_id' in global_config:
            conf['id'] = global_config['cluster_id']
            del global_config['cluster_id']
        if 'appname' in global_config:
            conf['name'] = global_config['appname']
            del global_config['appname']

        conf['zones'] = zones
        if global_config:
            conf['config'] = global_config

        return conf