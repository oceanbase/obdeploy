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
from collections.abc import Iterable, Iterator

import os
import re
import sys
import getpass
import hashlib
from copy import deepcopy
from enum import Enum
from datetime import datetime

from ruamel.yaml.comments import CommentedMap

import _errno as err
from tool import ConfigUtil, FileUtil, YamlLoader, OrderedDict, COMMAND_ENV
from _manager import Manager
from _stdio import SafeStdio
from _environ import ENV_BASE_DIR


yaml = YamlLoader()
DEFAULT_CONFIG_PARSER_MANAGER = None
ENV = 'env'


class ParserError(Exception):
    pass


class UserConfig(object):

    DEFAULT = {
        'username': getpass.getuser(),
        'password': None,
        'key_file': None,
        'port': 22,
        'timeout': 30
    }

    def __init__(self, username=None, password=None, key_file=None, port=None, timeout=None):
        self.username = username if username else self.DEFAULT['username']
        self.password = password
        self.key_file = key_file if key_file else self.DEFAULT['key_file']
        self.port = port if port else self.DEFAULT['port']
        self.timeout = timeout if timeout else self.DEFAULT['timeout']

    def __str__(self):
        return '%s' % self.username

    def __repr__(self):
        return '<UserConfig: %s>' % self.__str__()


class ServerConfig(object):

    def __init__(self, ip, name=None):
        self.ip = ip
        self._name = name

    @property
    def name(self):
        return self._name if self._name else self.ip

    def __str__(self):
        return '%s(%s)' % (self._name, self.ip) if self._name else self.ip

    def __repr__(self):
        return '<%s>' % self.__str__()

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.ip == other.ip and self.name == other.name
        if isinstance(other, dict):
            return self.ip == other['ip'] and self.name == other['name']


class ServerConfigFlyweightFactory(object):

    _CACHE = {}

    @staticmethod
    def get_instance(ip, name=None):
        server = ServerConfig(ip, name)
        _key = server.__str__()
        if _key not in ServerConfigFlyweightFactory._CACHE:
            ServerConfigFlyweightFactory._CACHE[_key] = server
        return ServerConfigFlyweightFactory._CACHE[_key]


class RsyncConfig(object):

    RSYNC = 'runtime_dependencies'
    SOURCE_PATH = 'src_path'
    TARGET_PATH = 'target_path'


class InnerConfigItem(str):
    pass


class InnerConfigKey(object):

    keyword_symbol = "$_"

    @classmethod
    def is_keyword(cls, s):
        return s.startswith(cls.keyword_symbol)

    @classmethod
    def to_keyword(cls, key):
        return "{}{}".format(cls.keyword_symbol, key)

    @classmethod
    def keyword_to_str(cls, _keyword):
        return str(_keyword.replace(cls.keyword_symbol, '', 1))


class ComponentInnerConfig(dict):

    COMPONENT_GLOBAL_ATTRS = InnerConfigKey.to_keyword('component_global_attrs')

    def __init__(self, component_name, config):
        super(ComponentInnerConfig, self).__init__()
        self.component_name = component_name
        c_config = {}
        for server in config:
            i_config = {}
            s_config = config[server]
            for key in s_config:
                i_config[InnerConfigItem(key)] = s_config[key]
            c_config[server] = i_config
        self.update(c_config)

    def __iter__(self):
        keys = self.keys()
        servers = []
        for key in keys:
            if key != self.COMPONENT_GLOBAL_ATTRS:
                servers.append(key)
        return iter(servers)

    def update_server_config(self, server, key, value):
        self._update_config(server, key, value)

    def update_attr(self, key, value):
        self._update_config(self.COMPONENT_GLOBAL_ATTRS, key, value)

    def del_server_config(self, server, key):
        self._del_config(server, key)

    def del_attr(self, key):
        self._del_config(self.COMPONENT_GLOBAL_ATTRS, key)

    def get_attr(self, key):
        return self._get_config(self.COMPONENT_GLOBAL_ATTRS, key)

    def _update_config(self, item, key, value):
        if not self.__contains__(item):
            self[item] = {}
        if not InnerConfigKey.is_keyword(key):
            key = InnerConfigKey.to_keyword(key)
        self[item][key] = value

    def _del_config(self, item, key):
        if not self.__contains__(item):
            return
        if not InnerConfigKey.is_keyword(key):
            key = InnerConfigKey.to_keyword(key)
        if key in self[item]:
            del self[item][key]

    def _get_config(self, item, key):
        if not self.__contains__(item):
            return
        if not InnerConfigKey.is_keyword(key):
            key = InnerConfigKey.to_keyword(key)
        return self[item].get(key)


class InnerConfigKeywords(object):

    DEPLOY_INSTALL_MODE = 'deploy_install_mode'
    DEPLOY_BASE_DIR = 'deploy_base_dir'


class InnerConfig(object):

    def __init__(self, path, yaml_loader):
        self.path = path
        self.yaml_loader = yaml_loader
        self.config = {}
        self._load()

    def _load(self):
        self.config = {}
        try:
            with FileUtil.open(self.path, 'rb') as f:
                config = self.yaml_loader.load(f)
                for component_name in config:
                    if InnerConfigKey.is_keyword(component_name):
                        self.config[InnerConfigItem(component_name)] = config[component_name]
                    else:
                        self.config[component_name] = ComponentInnerConfig(component_name, config[component_name])
        except:
            pass

    def _dump(self):
        try:
            stdio = self.yaml_loader.stdio if self.yaml_loader else None
            with FileUtil.open(self.path, 'w', stdio=stdio) as f:
                self.yaml_loader.dump(self.config, f)
            return True
        except:
            pass
        return False

    def dump(self):
        return self._dump()

    def get_component_config(self, component_name):
        return self.config.get(component_name, {})

    def get_server_config(self, component_name, server):
        return self.get_component_config(component_name).get(server, {})

    def get_global_config(self, key, default=None):
        key = InnerConfigKey.to_keyword(key)
        return self.config.get(key, default)

    def update_global_config(self, key, value):
        self.config[InnerConfigKey.to_keyword(key)] = value

    def update_component_config(self, component_name, config):
        self.config[component_name] = {}
        for server in config:
            c_config = {}
            data = config[server]
            for key in data:
                if not isinstance(key, InnerConfigItem):
                    key = InnerConfigItem(key)
                c_config[key] = data[key]
            self.config[component_name][server] = c_config
        if ComponentInnerConfig.COMPONENT_GLOBAL_ATTRS in config:
            self.config[component_name][ComponentInnerConfig.COMPONENT_GLOBAL_ATTRS] = config[ComponentInnerConfig.COMPONENT_GLOBAL_ATTRS]


class ConfigParser(object):

    STYLE = ''
    INNER_CONFIG_MAP = {}
    PREFIX = '$_'
    META_KEYS = ['version', 'tag', 'release', 'package_hash']

    @classmethod
    def _is_inner_item(cls, key):
        return isinstance(key, InnerConfigItem) and key.startswith(cls.PREFIX)

    @classmethod
    def extract_inner_config(cls, cluster_config, config):
        return {}

    @staticmethod
    def _get_server(server_data):
        if isinstance(server_data, dict):
            ip = ConfigUtil.get_value_from_dict(server_data, 'ip', transform_func=str)
            name = ConfigUtil.get_value_from_dict(server_data, 'name', transform_func=str)
        else:
            ip = server_data
            name = None
        if not re.match(r'^((25[0-5]|2[0-4]\d|[01]?\d{1,2})\.){3}(25[0-5]|2[0-4]\d|[01]?\d{1,2})$', ip) \
                and not re.match(r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$', ip):
            raise Exception('Invalid ip address {}'.format(ip))
        return ServerConfigFlyweightFactory.get_instance(ip, name)

    @classmethod
    def _get_servers(cls, servers_data):
        servers = []
        for server_data in servers_data:
            servers.append(cls._get_server(server_data))
        return servers

    @classmethod
    def _to_cluster_config(cls, component_name, config, added_servers=None):
        raise NotImplementedError

    @classmethod
    def merge_config(cls, component_name, config, new_config):
        raise NotImplementedError

    @classmethod
    def to_cluster_config(cls, component_name, config, added_servers=None):
        cluster_config = cls._to_cluster_config(component_name, config, added_servers)
        cluster_config.set_include_file(config.get('include', ''))
        cluster_config.parser = cls
        return cluster_config

    @classmethod
    def _from_cluster_config(cls, conf, cluster_config):
        raise NotImplementedError

    @classmethod
    def from_cluster_config(cls, cluster_config):
        if not cls.STYLE:
            raise NotImplementedError('undefined Style ConfigParser')

        conf = CommentedMap()
        conf['style'] = cls.STYLE
        if cluster_config.origin_package_hash:
            conf['package_hash'] = cluster_config.origin_package_hash
        if cluster_config.origin_version:
            conf['version'] = cluster_config.origin_version
        if cluster_config.origin_tag:
            conf['tag'] = cluster_config.origin_tag
        if cluster_config.origin_release:
            conf['release'] = cluster_config.origin_release
        if cluster_config.depends:
            conf['depends'] = list(cluster_config.depends)
        conf = cls._from_cluster_config(conf, cluster_config)
        inner_config = cls.extract_inner_config(cluster_config, conf)
        return {
            'inner_config': inner_config,
            'config': conf
        }

    @classmethod
    def get_server_src_conf(cls, cluster_config, component_config, server):
        if server.name not in component_config:
            component_config[server.name] = {}
        return component_config[server.name]

    @classmethod
    def get_global_src_conf(cls, cluster_config, component_config):
        if 'global' not in component_config:
            component_config['global'] = {}
        return component_config['global']


class DefaultConfigParser(ConfigParser):

    STYLE = 'default'

    @classmethod
    def _to_cluster_config(cls, component_name, conf, added_servers=None):
        servers = cls._get_servers(conf.get('servers', []))
        cluster_config = ClusterConfig(
            servers,
            component_name,
            ConfigUtil.get_value_from_dict(conf, 'version', None, str),
            ConfigUtil.get_value_from_dict(conf, 'tag', None, str),
            ConfigUtil.get_value_from_dict(conf, 'release', None, str),
            ConfigUtil.get_value_from_dict(conf, 'package_hash', None, str)
        )
        if added_servers:
            cluster_config.added_servers = added_servers
        if 'global' in conf:
            cluster_config.set_global_conf(conf['global'])

        if RsyncConfig.RSYNC in conf:
            cluster_config.set_rsync_list(conf[RsyncConfig.RSYNC])

        if ENV in conf:
            cluster_config.set_environments(conf[ENV])

        for server in servers:
            if server.name in conf:
                cluster_config.add_server_conf(server, conf[server.name])
        return cluster_config

    @classmethod
    def merge_config(cls, component_name, config, new_config):
        unmergeable_keys = cls.META_KEYS + ['global', RsyncConfig.RSYNC, ENV]
        for key in unmergeable_keys:
            assert key not in new_config, Exception('{} is not allowed to be set in additional conf'.format(key))
        servers = cls._get_servers(config.get('servers', []))
        merge_servers = cls._get_servers(new_config.get('servers', []))
        for server in merge_servers:
            assert server not in servers, Exception('{} is already in cluster'.format(server))
        config['servers'] = config.get('servers', []) + new_config.get('servers', [])
        merge_server_names = [server.name for server in merge_servers]
        for key in merge_server_names:
            if key in new_config:
                config[key] = new_config[key]
        return cls.to_cluster_config(component_name, config, merge_servers)

    @classmethod
    def extract_inner_config(cls, cluster_config, config):
        inner_config = cluster_config.get_inner_config()
        for server in cluster_config.servers:
            if server.name not in inner_config:
                inner_config[server.name] = {}

        global_config = config.get('global', {})
        keys = list(global_config.keys())
        for key in keys:
            if cls._is_inner_item(key):
                for server in cluster_config.servers:
                    inner_config[server.name][key] = global_config[key]
                del global_config[key]

        for server in cluster_config.servers:
            if server.name not in config:
                continue
            server_config = config[server.name]
            keys = list(server_config.keys())
            for key in keys:
                if cls._is_inner_item(key):
                    inner_config[server.name][key] = server_config[key]
                    del server_config[key]
        return inner_config

    @classmethod
    def _from_cluster_config(cls, conf, cluster_config):
        conf['servers'] = []
        for server in cluster_config.servers:
            if server.name == server.ip:
                conf['servers'].append(server.name)
            else:
                conf['servers'].append({'name': server.name, 'ip': server.ip})

        if cluster_config.get_original_global_conf():
            conf['global'] = cluster_config.get_original_global_conf()
        for server in cluster_config.servers:
            server_config = cluster_config.get_original_server_conf(server)
            if server_config:
                conf[server.name] = server_config
        return conf


class ClusterConfig(object):

    def __init__(self, servers, name, version, tag, release, package_hash, parser=None):
        self._version = version
        self.origin_version = version
        self.tag = tag
        self.origin_tag = tag
        self._release = release
        self.origin_release = release
        self.name = name
        self.origin_package_hash = package_hash
        self._package_hash = package_hash
        self._temp_conf = {}
        self._all_default_conf = {}
        self._default_conf = {}
        self._global_conf = None
        self._server_conf = {}
        self._cache_server = {}
        self._original_global_conf = {}
        self._rsync_list = None
        self._include_config = None
        self._origin_rsync_list = {}
        self._include_file = None
        self._origin_include_file = None
        self._origin_include_config = None
        self._unprocessed_global_conf = None
        self._unprocessed_server_conf = {}
        self._environments = None
        self._origin_environments = {}
        self._inner_config = {}
        self._base_dir = ''
        servers = list(servers)
        self.servers = servers
        self._original_servers = servers # 保证顺序
        for server in servers:
            self._server_conf[server] = {}
            self._cache_server[server] = None
        self._deploy_config = None
        self._depends = {}
        self._be_depends = {}
        self.parser = parser
        self._has_package_pattern = None
        self._object_hash = None
        self.added_servers = []

    if sys.version_info.major == 2:
        def __hash__(self):
            if self._object_hash is None:
                m_sum = hashlib.md5()
                m_sum.update(str(self.package_hash).encode('utf-8'))
                m_sum.update(str(self.get_global_conf()).encode('utf-8'))
                for server in self.servers:
                    m_sum.update(str(self.get_server_conf(server)).encode('utf-8'))
                m_sum.update(str(self.depends).encode('utf-8'))
                self._object_hash = int(''.join(['%03d' % ord(v) for v in m_sum.digest()]))
            return self._object_hash
    else:
        def __hash__(self):
            if self._object_hash is None:
                m_sum = hashlib.md5()
                m_sum.update(str(self.package_hash).encode('utf-8'))
                m_sum.update(str(self.get_global_conf()).encode('utf-8'))
                for server in self.servers:
                    m_sum.update(str(self.get_server_conf(server)).encode('utf-8'))
                m_sum.update(str(self.depends).encode('utf-8'))
                self._object_hash = (int(''.join(['%03d' % v for v in m_sum.digest()])))
            return self._object_hash

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        # todo 检查 rsync include等
        if self.servers != other.servers:
            return False
        if self.get_global_conf() != other.get_global_conf():
            return False
        for server in self.servers:
            if self.get_server_conf(server) != other.get_server_conf(server):
                return False
        return True

    def __deepcopy__(self, memo):
        cluster_config = self.__class__(deepcopy(self.servers), self.name, self.version, self.tag, self.release, self.package_hash, self.parser)
        copy_attrs = ['origin_tag', 'origin_version', 'origin_package_hash', 'parser', 'added_servers']
        deepcopy_attrs = ['_temp_conf', '_all_default_conf', '_default_conf', '_global_conf', '_server_conf', '_cache_server', '_original_global_conf', '_depends', '_original_servers', '_inner_config']
        for attr in copy_attrs:
            setattr(cluster_config, attr, getattr(self, attr))
        for attr in deepcopy_attrs:
            setattr(cluster_config, attr, deepcopy(getattr(self, attr)))
        return cluster_config

    def set_deploy_config(self, _deploy_config):
        if self._deploy_config is None:
            self._deploy_config = _deploy_config
            self.set_base_dir(self._deploy_config.get_base_dir())
            return True
        return False

    def set_base_dir(self, base_dir):
        if self._base_dir != base_dir:
            self._base_dir = base_dir
            self._rsync_list = None
            self._include_config = None
            self._global_conf = None

    @property
    def deploy_name(self):
        return self._deploy_config.name

    @property
    def original_servers(self):
        return self._original_servers

    @property
    def depends(self):
        return self._depends.keys()
    
    @property
    def be_depends(self):
        return self._be_depends.keys()

    def _clear_cache_server(self):
        for server in self._cache_server:
            self._cache_server[server] = None
            if server in self._unprocessed_server_conf:
                del self._unprocessed_server_conf[server]

    def get_inner_config(self):
        return self._inner_config
    
    def update_component_attr(self, key, value, save=True):
        self._inner_config.update_attr(key, value)
        return self._deploy_config.dump() if save else True
    
    def del_component_attr(self, key, save=True):
        self._inner_config.del_attr(key)
        return self._deploy_config.dump() if save else True
    
    def get_component_attr(self, key):
        return self._inner_config.get_attr(key)
    
    def is_cp_install_mode(self):
        return self._deploy_config.is_cp_install_mode()

    def is_ln_install_mode(self):
        return self._deploy_config.is_ln_install_mode()

    def apply_inner_config(self, config):
        if not isinstance(config, ComponentInnerConfig):
            config = ComponentInnerConfig(self.name, {} if config is None else config)
        self._inner_config = config
        self._clear_cache_server()

    def add_depend(self, name, cluster_conf):
        if self.name == name:
            raise Exception('Can not set %s as %s\'s dependency' % (name, name))
        if self.name in cluster_conf.depends:
            raise Exception('Circular Dependency: %s and %s' % (self.name, name))
        self._depends[name] = cluster_conf
        cluster_conf.add_be_depend(self.name, self)

    def add_be_depend(self, name, cluster_conf):
        if self.name == name:
            raise Exception('Can not set %s as %s\'s dependency' % (name, name))
        if self.name not in cluster_conf.depends:
            raise Exception('%s is not %s\'s dependency' % (self.name, name))
        if self.name in cluster_conf.be_depends:
            raise Exception('Circular Dependency: %s and %s' % (self.name, name))
        self._be_depends[name] = cluster_conf

    def add_depend_component(self, depend_component_name):
        return self._deploy_config.add_depend_for_component(self.name, depend_component_name, save=False)

    def del_depend(self, name, component_name):
        if component_name in self._depends:
            del self._depends[component_name]

    def get_depend_servers(self, name):
        if name not in self._depends:
            return []
        cluster_config = self._depends[name]
        return deepcopy(cluster_config.original_servers)
    
    def get_be_depend_servers(self, name):
        if name not in self._be_depends:
            return []
        cluster_config = self._be_depends[name]
        return deepcopy(cluster_config.original_servers)
        
    def get_depend_added_servers(self, name):
        if name not in self._depends:
            return None
        cluster_config = self._depends[name]
        return deepcopy(cluster_config.added_servers)
    
    def get_deploy_added_components(self):
        return self._deploy_config.added_components
    
    def get_deploy_changed_components(self):
        return self._deploy_config.changed_components

    def get_deploy_removed_components(self):
        return self._deploy_config.removed_components
        
    def get_depend_config(self, name, server=None, with_default=True):
        if name not in self._depends:
            return None
        cluster_config = self._depends[name]
        if with_default:
            config = cluster_config.get_server_conf_with_default(server) if server else cluster_config.get_global_conf_with_default()
        else:
            config = cluster_config.get_server_conf(server) if server else cluster_config.get_global_conf()
        return deepcopy(config)

    def get_be_depend_config(self, name, server=None, with_default=True):
        if name not in self._be_depends:
            return None
        cluster_config = self._be_depends[name]
        if with_default:
            config = cluster_config.get_server_conf_with_default(server) if server else cluster_config.get_global_conf_with_default()
        else:
            config = cluster_config.get_server_conf(server) if server else cluster_config.get_global_conf()
        return deepcopy(config)

    def update_server_conf(self, server, key, value, save=True):
        if self._deploy_config is None:
            return False
        if server not in self._server_conf:
            return False
        if self._temp_conf and key in self._temp_conf:
            value = self._temp_conf[key].param_type(value).value
        if not self._deploy_config.update_component_server_conf(self.name, server, key, value, save):
            return False
        self._server_conf[server][key] = value
        if self._cache_server[server] is not None:
            self._cache_server[server][key] = value
        return True

    def update_global_conf(self, key, value, save=True):
        if self._deploy_config is None:
            return False
        if self._temp_conf and key in self._temp_conf:
            value = self._temp_conf[key].param_type(value).value
        if not self._deploy_config.update_component_global_conf(self.name, key, value, save):
            return False
        self._update_global_conf(key, value)
        return True

    def _update_global_conf(self, key, value):
        self._original_global_conf[key] = value
        self._global_conf = None
        self._unprocessed_global_conf = None
        self._clear_cache_server()

    def update_rsync_list(self, rsync_list, save=True):
        if self._deploy_config is None:
            return False
        if not self._deploy_config.update_component_rsync_list(self.name, rsync_list, save):
            return False
        self._rsync_list = rsync_list
        return True

    def update_environments(self, environments, save=True):
        if self._deploy_config is None:
            return False
        if not self._deploy_config.update_component_environments(self.name, environments, save):
            return False
        self._origin_environments = environments
        self._environments = None
        return True

    def get_unconfigured_require_item(self, server, skip_keys=[]):
        items = []
        config = self._get_unprocessed_server_conf(server)
        if config is not None:
            for key in self._temp_conf:
                if key in skip_keys:
                    continue
                if not self._temp_conf[key].require:
                    continue
                if key in config:
                    continue
                items.append(key)
        return items

    def get_server_conf_with_default(self, server):
        if server not in self._server_conf:
            return None
        config = deepcopy(self._all_default_conf)
        server_config = self.get_server_conf(server)
        if server_config:
            config.update(server_config)
        return config

    def get_need_redeploy_items(self, server):
        if server not in self._server_conf:
            return None
        items = {}
        config = self.get_server_conf(server)
        for key in config:
            if key in self._temp_conf and self._temp_conf[key].need_redeploy:
                items[key] = config[key]
        return items

    def get_need_restart_items(self, server):
        if server not in self._server_conf:
            return None
        items = {}
        config = self.get_server_conf(server)
        for key in config:
            if key in self._temp_conf and self._temp_conf[key].need_restart:
                items[key] = config[key]
        return items
        
    def update_temp_conf(self, temp_conf):
        self._default_conf = {}
        self._all_default_conf = {}
        self._temp_conf = temp_conf
        for key in self._temp_conf:
            if self._temp_conf[key].require and self._temp_conf[key].default is not None:
                self._default_conf[key] = self._temp_conf[key].default
            if self._temp_conf[key].default is not None:
                self._all_default_conf[key] = self._temp_conf[key].default
        self._global_conf = None
        self._unprocessed_global_conf = None
        self._clear_cache_server()

    def _apply_temp_conf(self, conf):
        if self._temp_conf:
            for key in conf:
                if key in self._temp_conf:
                    conf[key] = self._temp_conf[key].param_type(conf[key]).value
        return conf

    def get_temp_conf_item(self, key):
        if self._temp_conf:
            return self._temp_conf.get(key)
        else:
            return None

    def check_param(self):
        errors = []
        if self._temp_conf:
            _, g_errs = self.global_check_param()
            errors += g_errs
            for server in self._server_conf:
                s_errs, _ = self._check_param(self._server_conf[server])
                errors += s_errs
        return not errors, set(errors)

    def global_check_param(self):
        errors = []
        if self._temp_conf:
            errors, _ = self._check_param(self._get_unprocessed_global_conf())
        return not errors, errors

    def servers_check_param(self):
        check_res = {}
        if self._temp_conf:
            global_config = self._get_unprocessed_global_conf()
            for server in self._server_conf:
                config = deepcopy(self._server_conf[server])
                config.update(global_config)
                errors, items = self._check_param(config)
                check_res[server] = {'errors': errors, 'items': items}
        return check_res

    def _check_param(self, config):
        errors = []
        items = []
        for key in config:
            item = self._temp_conf.get(key)
            if item:
                try:
                    item.check_value(config[key])
                except Exception as e:
                    errors.append(str(e))
                    items.append(item)
        return errors, items

    def set_global_conf(self, conf):
        if not isinstance(conf, dict):
            raise Exception('%s global config is not a dictionary. Please check the syntax of your configuration file.\n See https://github.com/oceanbase/obdeploy/blob/master/docs/zh-CN/4.configuration-file-description.md' % self.name)
        self._original_global_conf = deepcopy(conf)
        self._global_conf = None
        self._clear_cache_server()

    def set_rsync_list(self, configs):
        self._origin_rsync_list = configs

    def set_include_file(self, path):
        if path != self._origin_include_file:
            self._origin_include_file = path
            self._include_file = None
            self._include_config = None

    def set_environments(self, config):
        self._origin_environments = config
        self._environments = None

    def add_server_conf(self, server, conf):
        if server not in self.servers:
            self.servers.append(server)
        if server not in self._original_servers:
            self._original_servers.append(server)
        self._server_conf[server] = conf
        self._cache_server[server] = None

    def _get_unprocessed_global_conf(self):
        if self._unprocessed_global_conf is None:
            self._unprocessed_global_conf = deepcopy(self._default_conf)
            self._unprocessed_global_conf.update(self._get_include_config('config', {}))
            if self._original_global_conf:
                self._unprocessed_global_conf.update(self._original_global_conf)
        return self._unprocessed_global_conf

    def get_global_conf(self):
        if self._global_conf is None:
            self._global_conf = self._apply_temp_conf(self._get_unprocessed_global_conf())
        return self._global_conf

    def get_global_conf_with_default(self):
        config = deepcopy(self._all_default_conf)
        config.update(self.get_global_conf())
        return config

    def _add_base_dir(self, path):
        if not os.path.isabs(path):
            if self._base_dir:
                path = os.path.join(self._base_dir, path)
            else:
                raise Exception("`{}` need to use absolute paths. If you want to use relative paths, please enable developer mode "
                "and set environment variables {}".format(RsyncConfig.RSYNC, ENV_BASE_DIR))
        return path

    @property
    def has_package_pattern(self):
        if self._has_package_pattern is None:
            patterns = (self.origin_package_hash, self.origin_version, self.origin_release, self.origin_tag)
            self._has_package_pattern = any([x is not None for x in patterns])
        return self._has_package_pattern

    @property
    def version(self):
        if self._version is None:
            self._version = self.config_version
        return self._version

    @version.setter
    def version(self, value):
        self._version = value

    @property
    def config_version(self):
        if not self.has_package_pattern:
            return self._get_include_config('version', None)
        else:
            return self.origin_version

    @property
    def release(self):
        if self._release is None:
            self._release = self.config_release
        return self._release

    @release.setter
    def release(self, value):
        self._release = value

    @property
    def config_release(self):
        if not self.has_package_pattern:
            return self._get_include_config('release', None)
        else:
            return self.origin_release

    @property
    def package_hash(self):
        if self._package_hash is None:
            self._package_hash = self.config_package_hash
        return self._package_hash

    @package_hash.setter
    def package_hash(self, value):
        self._package_hash = value

    @property
    def config_package_hash(self):
        if not self.has_package_pattern:
            return self._get_include_config('package_hash', None)
        else:
            return self.origin_package_hash
    
    def _get_include_config(self, key=None, default=None, not_found_act="ignore"):
        if self._include_config is None:
            if self._origin_include_file:
                if os.path.isabs(self._origin_include_file):
                    include_file = self._origin_include_file
                else:
                    include_file = os.path.join(self._base_dir, self._origin_include_file)
                if include_file != self._include_file:
                    self._include_file = include_file
                    self._origin_include_config = self._deploy_config.load_include_file(self._include_file)
            if self._origin_include_config is None:
                self._origin_include_config = {}
            self._include_config = self._origin_include_config
        value = self._include_config.get(key, default) if key else self._include_config
        return deepcopy(value)

    def get_rsync_list(self):
        if self._rsync_list is None:
            self._rsync_list = self._get_include_config(RsyncConfig.RSYNC, [])
            self._rsync_list += self._origin_rsync_list
            for item in self._rsync_list:
                item[RsyncConfig.SOURCE_PATH] = self._add_base_dir(item[RsyncConfig.SOURCE_PATH])
        return self._rsync_list

    def get_environments(self):
        if self._environments is None:
            self._environments = self._get_include_config(ENV, OrderedDict())
            self._environments.update(self._origin_environments)
        return self._environments

    def _get_unprocessed_server_conf(self, server):
        if server not in self._unprocessed_server_conf:
            conf = deepcopy(self._inner_config.get(server.name, {}))
            conf.update(self._get_unprocessed_global_conf())
            conf.update(self._server_conf[server])
            self._unprocessed_server_conf[server] = conf
        return self._unprocessed_server_conf[server]

    def get_server_conf(self, server):
        if server not in self._server_conf:
            return None
        if self._cache_server[server] is None:
            self._cache_server[server] = self._apply_temp_conf(self._get_unprocessed_server_conf(server))
        return self._cache_server[server]

    def get_original_global_conf(self, format_conf=False):
        conf = deepcopy(self._original_global_conf)
        format_conf and self._apply_temp_conf(conf)
        return conf

    def get_original_server_conf(self, server, format_conf=False):
        conf = deepcopy(self._server_conf.get(server))
        format_conf and self._apply_temp_conf(conf)
        return conf

    def get_original_server_conf_with_global(self, server, format_conf=False):
        config = deepcopy(self.get_original_global_conf())
        config.update(self._server_conf.get(server, {}))
        format_conf and self._apply_temp_conf(config)
        return config


class DeployStatus(Enum):

    STATUS_CONFIGUREING = 'configuring'
    STATUS_CONFIGURED = 'configured'
    STATUS_DEPLOYING = 'delopying'
    STATUS_DEPLOYED = 'deployed'
    STATUS_RUNNING = 'running'
    STATUS_STOPING = 'stoping'
    STATUS_STOPPED = 'stopped'
    STATUS_DESTROYING = 'destroying'
    STATUS_DESTROYED = 'destroyed'
    STATUS_UPRADEING = 'upgrading'


class ClusterStatus(Enum):

    STATUS_RUNNING = 1  # running
    STATUS_STOPPED = 0   # stopped

class DeployConfigStatus(Enum):

    UNCHNAGE = 'unchange'
    NEED_RELOAD = 'need reload'
    NEED_RESTART = 'need restart'
    NEED_REDEPLOY = 'need redeploy'


class  DeployInstallMode(object):

    LN = 'ln'
    CP = 'cp'


class DeployInfo(object):

    def __init__(self, name, status, components=None, config_status=DeployConfigStatus.UNCHNAGE, create_date=None):
        self.status = status
        self.name = name
        self.components = components if components else {}
        self.config_status = config_status
        self.create_date = create_date

    def __str__(self):
        info = ['%s (%s)' % (self.name, self.status.value)]
        for name in self.components:
            info.append('%s-%s' % (name, self.components[name]))
        return '\n'.join(info)


class DeployConfig(SafeStdio):

    def __init__(self, yaml_path, yaml_loader=yaml, inner_config=None, config_parser_manager=None, stdio=None):
        self._user = None
        self.unuse_lib_repository = False
        self.auto_create_tenant = False
        self._inner_config = inner_config
        self.components = OrderedDict()
        self._src_data = None
        self.name = os.path.split(os.path.split(yaml_path)[0])[-1]
        self.yaml_path = yaml_path
        self.yaml_loader = yaml_loader
        self.config_parser_manager = config_parser_manager if config_parser_manager else DEFAULT_CONFIG_PARSER_MANAGER
        self.stdio = stdio
        self._ignore_include_error = False
        if self.config_parser_manager is None:
            raise ParserError('ConfigParserManager Not Set')
        self._load()
        self._added_components = []
        self._changed_components = []
        self._removed_components = set()
        self._do_not_dump = False
        self._mem_mode = False

    def __deepcopy__(self, memo):
        deploy_config = self.__class__(self.yaml_path, self.yaml_loader, self._inner_config, self.config_parser_manager, self.stdio)
        for component_name in self.components:
            deploy_config.components[component_name] = deepcopy(self.components[component_name])
        return deploy_config

    def set_undumpable(self):
        self._do_not_dump = True

    def set_dumpable(self):
        self._do_not_dump = False

    def enable_mem_mode(self):
        self._mem_mode = True

    def disable_mem_mode(self):
        self._mem_mode = False

    @property
    def user(self):
        return self._user

    @property
    def inner_config(self):
        return self._inner_config

    @inner_config.setter
    def inner_config(self, inner_config):
        if inner_config:
            def get_inner_config(component_name):
                return inner_config.get_component_config(component_name)
        else:
            def get_inner_config(component_name):
                return ComponentInnerConfig(component_name, {})

        self._inner_config = inner_config
        base_dir = self.get_base_dir()
        for component_name in self.components:
            cluster_config = self.components[component_name]
            cluster_config.apply_inner_config(get_inner_config(component_name))
            cluster_config.set_base_dir(base_dir)

    @property
    def added_components(self):
        if self._added_components:
            return self._added_components
        elif self._changed_components or self._removed_components:
            # It's means that the components have been changed, so must not be added
            return []
        else:
            # Maybe the deploy is new, so all components are added
            return self.components.keys()
        
    @property
    def changed_components(self):
        return self._changed_components

    @property
    def removed_components(self):
        return self._removed_components

    def get_added_servers(self, component_name):
        if component_name not in self.components:
            raise Exception('No such component {}'.format(component_name))
        return self.components[component_name].added_servers

    def set_unuse_lib_repository(self, status):
        if self.unuse_lib_repository != status:
            self.unuse_lib_repository = status
            self._src_data['unuse_lib_repository'] = status
            return self._dump()
        return True

    def set_auto_create_tenant(self, status):
        if self.auto_create_tenant != status:
            self.auto_create_tenant = status
            self._src_data['auto_create_tenant'] = status
            return self._dump()
        return True

    def update_component_info(self, repository):
        component = repository.name
        if component not in self.components:
            return False
        ori_data = self._src_data[component]
        src_data = deepcopy(ori_data)

        if 'package_hash' in src_data:
            src_data['package_hash'] = repository.hash
        if 'version' in src_data:
            src_data['version'] = repository.version
        if 'release' in src_data:
            src_data['release'] = repository.release
        if 'tag' in src_data:
            del src_data['tag']

        self._src_data[component] = src_data
        if self._dump():
            cluster_config = self.components[component]
            cluster_config.package_hash = repository.hash
            cluster_config.version = repository.version
            cluster_config.release = repository.release
            cluster_config.tag = None
            return True
        self._src_data[component] = ori_data
        return False

    def _load(self):
        try:
            with open(self.yaml_path, 'rb') as f:
                depends = {}
                self._src_data = self.yaml_loader.load(f)
                for key in self._src_data:
                    if key == 'user':
                        self.set_user_conf(UserConfig(
                            ConfigUtil.get_value_from_dict(self._src_data[key], 'username'),
                            ConfigUtil.get_value_from_dict(self._src_data[key], 'password'),
                            ConfigUtil.get_value_from_dict(self._src_data[key], 'key_file'),
                            ConfigUtil.get_value_from_dict(self._src_data[key], 'port', 0, int),
                            ConfigUtil.get_value_from_dict(self._src_data[key], 'timeout', 0, int),
                        ))
                    elif key == 'unuse_lib_repository':
                        self.unuse_lib_repository = self._src_data['unuse_lib_repository']
                    elif key == 'auto_create_tenant':
                        self.auto_create_tenant = self._src_data['auto_create_tenant']
                    elif issubclass(type(self._src_data[key]), dict):
                        self._add_component(key, self._src_data[key])
                        depends[key] = self._src_data[key].get('depends', [])
                for comp in depends:
                    conf = self.components[comp]
                    for name in depends[comp]:
                        if name == comp:
                            continue
                        if name in self.components:
                            conf.add_depend(name, self.components[name]) 
        except:
            self.stdio.exception()
        if not self.user:
            self.set_user_conf(UserConfig())

    def scale_out(self, config_path):
        ret = True
        depends = {}
        try:
            with FileUtil.open(config_path, 'rb') as f:
                source_data = self.yaml_loader.load(f)
                for key in source_data:
                    if key in ['user', 'unuse_lib_repository', 'auto_create_tenant']:
                        self.stdio.error(err.EC_COMPONENT_CHANGE_CONFIG.format(message=key))
                        ret = False
                    elif issubclass(type(source_data[key]), dict):
                        new_depends = source_data[key].get('depends', [])
                        if key not in self.components:
                            self.stdio.error(err.EC_COMPONENT_NOT_EXISTS.format(component=key))
                            ret = False
                            break
                        if new_depends and new_depends != self.components[key].depends:
                            self.stdio.error(err.EC_COMPONENT_CHANGE_CONFIG.format(message='depends:{}'.format(key)))
                            ret = False
                        # temp _depends
                        depends[key] = self.components[key].depends

                    if not self._merge_component(key, source_data[key]):
                        ret = False

                for comp in depends:
                    conf = self.components[comp]
                    for name in depends[comp]:
                        if name == comp:
                            continue
                        if name in self.components:
                            conf.add_depend(name, self.components[name])     
        except Exception as e:
            self.stdio.exception(e)
            ret = False
        return ret

    def add_components(self, config_path, ignore_exist=False):
        ret = True
        depends = {}
        try:
            with FileUtil.open(config_path, 'rb') as f:
                source_data = self.yaml_loader.load(f)
                for key in source_data:
                    if key in ['user', 'unuse_lib_repository', 'auto_create_tenant']:
                        self.stdio.error(err.EC_COMPONENT_CHANGE_CONFIG.format(message=key))
                        ret = False
                    elif issubclass(type(source_data[key]), dict):
                        if key in self.components:
                            if ignore_exist:
                                continue
                            self.stdio.error(err.EC_COMPONENT_EXISTS.format(component=key))
                            ret = False
                            continue
                        self._add_component(key, source_data[key])
                        if not self.update_component(self.components[key]):
                            self.stdio.error(err.EC_COMPONENT_FAIL_TO_UPDATE_CONFIG.format(component=key))
                            ret = False
                        depends[key] = source_data[key].get('depends', [])
                        self._added_components.append(key)
        except Exception as e:
            self.stdio.exception(e)
            ret = False

        for comp in depends:
            for name in depends[comp]:
                self.add_depend_for_component(comp, name, save=False)
        return ret

    def del_components(self, components, dryrun=False):
        ret = True
        src_data = deepcopy(self._src_data) if dryrun else self._src_data
        component_map = deepcopy(self.components) if dryrun else self.components
        for del_comp in components:
            if del_comp not in component_map:
                self.stdio.error(err.EC_COMPONENT_NOT_EXISTS.format(component=del_comp))
                ret = False
                continue
            del component_map[del_comp]
            del src_data[del_comp]
            self.removed_components.add(del_comp)
        for comp_name in component_map:
            for del_comp in components:
                if del_comp in component_map[comp_name].depends:
                    self.stdio.error(err.EC_COMPONENT_REMOVE_DEPENDS.format(component1=del_comp, component2=comp_name))
                    ret = False
        if not component_map:
            self.stdio.error(err.EC_COMPONENT_NO_REMAINING_COMPS)
            ret = False
        return ret

    def allow_include_error(self):
        self.stdio.verbose("allow include file not exists")
        self._ignore_include_error = True

    def load_include_file(self, path):
        if not os.path.isabs(path):
            raise Exception("`{}` need to use absolute path. If you want to use relative paths, please enable developer mode "
            "and set environment variables {}".format('include', ENV_BASE_DIR))
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                return self.yaml_loader.load(f)
        else:
            if self._ignore_include_error:
                self.stdio.warn("include file: {} not found, some configurations may be lost".format(path))
                return {}
            else:
                raise Exception('Not such file: %s' % path)

    def _separate_config(self):
        if self.inner_config:
            for component_name in self.components:
                cluster_config = self.components[component_name]
                src_data = self._src_data[component_name]
                parser = cluster_config.parser
                if parser:
                    inner_config = parser.extract_inner_config(cluster_config, src_data)
                    self.inner_config.update_component_config(component_name, inner_config)

    def _dump_inner_config(self):
        if self.inner_config:
            self._separate_config()
            self.inner_config.dump()

    def _dump(self):
        if self._do_not_dump:
            raise Exception("Cannot dump because flag DO NOT DUMP exists.")
        try:
            with open(self.yaml_path, 'w') as f:
                self._dump_inner_config()
                self.yaml_loader.dump(self._src_data, f)
            return True
        except:
            import logging
            logging.exception('')
            pass
        return False

    def dump(self):
        return self._dump()

    def _update_global_inner_config(self, key, value, save=True):
        if self.inner_config:
            self.inner_config.update_global_config(key, value)
        return self._dump_inner_config() if save else True

    def _get_global_inner_config(self, key, default=None):
        if self.inner_config:
            return self.inner_config.get_global_config(key, default)
        return default

    def set_base_dir(self, path, save=True):
        if path and not os.path.isabs(path):
            raise Exception('%s is not an absolute path' % path)
        if self._update_global_inner_config(InnerConfigKeywords.DEPLOY_BASE_DIR, path, save=save):
            for component_name in self.components:
                cluster_config = self.components[component_name]
                cluster_config.set_base_dir(path)
            return True
        return False

    def get_base_dir(self):
        return self._get_global_inner_config(InnerConfigKeywords.DEPLOY_BASE_DIR, '')

    def set_deploy_install_mode(self, mode, save=True):
        return self._update_global_inner_config(InnerConfigKeywords.DEPLOY_INSTALL_MODE, mode, save=save)

    def get_deploy_install_mode(self):
        return self._get_global_inner_config(InnerConfigKeywords.DEPLOY_INSTALL_MODE, DeployInstallMode.CP)

    def enable_ln_install_mode(self, save=True):
        return self.set_deploy_install_mode(DeployInstallMode.LN, save=save)

    def enable_cp_install_mode(self, save=True):
        return self.set_deploy_install_mode(DeployInstallMode.CP, save=save)

    def is_ln_install_mode(self):
        return self.get_deploy_install_mode() == DeployInstallMode.LN

    def is_cp_install_mode(self):
        return self.get_deploy_install_mode() == DeployInstallMode.CP

    def set_user_conf(self, conf):
        self._user = conf

    def add_depend_for_component(self, component_name, depend_component_name, save=True):
        if component_name not in self.components:
            return False
        if depend_component_name not in self.components:
            return False
        cluster_config = self.components[component_name]
        if depend_component_name in cluster_config.depends:
            return True
        cluster_config.add_depend(depend_component_name, self.components[depend_component_name])
        component_config = self._src_data[component_name]
        if 'depends' not in component_config:
            component_config['depends'] = []
        component_config['depends'].append(depend_component_name)
        return self.dump() if save else True

    def del_depend_for_component(self, component_name, depend_component_name, save=True):
        if component_name not in self.components:
            return False
        if depend_component_name not in self.components:
            return False
        cluster_config = self.components[component_name]
        if depend_component_name not in cluster_config.depends:
            return True
        cluster_config.del_depend(depend_component_name, depend_component_name)
        component_config = self._src_data[component_name]
        component_config['depends'] = cluster_config.depends
        return self.dump() if save else True

    def update_component_server_conf(self, component_name, server, key, value, save=True):
        if self._mem_mode: 
            return True
        if component_name not in self.components:
            return False
        cluster_config = self.components[component_name]
        if server not in cluster_config.servers:
            return False
        component_config = cluster_config.parser.get_server_src_conf(cluster_config, self._src_data[component_name], server)
        component_config[key] = value
        return self.dump() if save else True

    def update_component_global_conf(self, component_name, key, value, save=True):
        if self._mem_mode:
            return True
        if component_name not in self.components:
            return False
        cluster_config = self.components[component_name]
        component_config = cluster_config.parser.get_global_src_conf(cluster_config, self._src_data[component_name])
        component_config[key] = value
        return self.dump() if save else True

    def _set_component(self, cluster_config):
        cluster_config.set_deploy_config(self)
        if self.inner_config:
            inner_config = self.inner_config.get_component_config(cluster_config.name)
            if inner_config:
                cluster_config.apply_inner_config(inner_config)
        self.components[cluster_config.name] = cluster_config

    def update_component(self, cluster_config):
        component_name = cluster_config.name
        if cluster_config.parser:
            parser = cluster_config.parser
        else:
            conf = self._src_data.get('component_name', {})
            style = conf.get('style', 'default')
            parser = self.config_parser_manager.get_parser(component_name, style)

        conf = parser.from_cluster_config(cluster_config)
        if component_name in self.components:
            self.components[component_name].set_deploy_config(None)
        cluster_config = deepcopy(cluster_config)
        cluster_config.apply_inner_config(conf['inner_config'])
        if self.inner_config:
            self.inner_config.update_component_config(component_name, conf['inner_config'])
        self._src_data[component_name] = conf['config']
        self._set_component(cluster_config)
        return True

    def _add_component(self, component_name, conf):
        self._set_component(self._parse_cluster_config(component_name, conf))

    def _parse_cluster_config(self, component_name, conf):
        parser = self.config_parser_manager.get_parser(component_name, conf.get('style'))
        return parser.to_cluster_config(component_name, conf)

    def _merge_component(self, component_name, conf):
        if component_name not in self.components:
            self.stdio.error('No such component {}'.format(component_name))
            return False
        parser = self.config_parser_manager.get_parser(component_name, conf.get('style'))
        cluster_config = self.components[component_name]
        if parser != cluster_config.parser:
            self.stdio.error('The style of the added configuration do not match the style of the existing cluster')
            return False
        src_conf = parser.from_cluster_config(cluster_config)

        global_attr = {}
        if ComponentInnerConfig.COMPONENT_GLOBAL_ATTRS in src_conf['inner_config']:
            global_attr = deepcopy(src_conf['inner_config'][(ComponentInnerConfig.COMPONENT_GLOBAL_ATTRS)])
        try:
            merged_cluster_config = parser.merge_config(component_name, src_conf['config'], conf)
            self._src_data[component_name] = src_conf['config']
            self._set_component(merged_cluster_config)
        except Exception as e:
            self.stdio.exception(err.EC_COMPONENT_FAILED_TO_MERGE_CONFIG.format(message=str(e)))
            return False
        
        cluster_config = self.components[component_name]
        for k in global_attr:
            v = global_attr.get(k)
            cluster_config.update_component_attr(k, v, save=False)
        self._changed_components.append(component_name)
        return True

    def change_component_config_style(self, component_name, style):
        if component_name not in self.components:
            return False

        parser = self.config_parser_manager.get_parser(component_name, style)
        cluster_config = self.components[component_name]
        if cluster_config.parser != parser:
            new_config = parser.from_cluster_config(cluster_config)
            self._add_component(component_name, new_config)
            self.components[component_name].apply_inner_config(new_config['inner_config'])
            if self.inner_config:
                self.inner_config.update_component_config(component_name, new_config['inner_config'])
            self._src_data[component_name] = new_config['config']
        return True


class Deploy(object):

    DEPLOY_STATUS_FILE = '.data'
    DEPLOY_YAML_NAME = 'config.yaml'
    INNER_CONFIG_NAME = 'inner_config.yaml'
    UPRADE_META_NAME = '.upgrade'

    def __init__(self, config_dir, config_parser_manager=None, stdio=None):
        self.config_dir = config_dir
        self.name = os.path.split(config_dir)[1]
        self._info = None
        self._config = None
        self.stdio = stdio
        self.config_parser_manager = config_parser_manager
        self._uprade_meta = None

    def use_model(self, name, repository, dump=True):
        self.deploy_info.components[name] = {
            'hash': repository.hash,
            'version': repository.version
        }
        return self.dump_deploy_info() if dump else True

    def unuse_model(self, name, dump=True):
        del self.deploy_info.components[name]
        return self.dump_deploy_info() if dump else True

    @staticmethod
    def get_deploy_file_path(path):
        return os.path.join(path, Deploy.DEPLOY_STATUS_FILE)

    @staticmethod
    def get_deploy_yaml_path(path):
        return os.path.join(path, Deploy.DEPLOY_YAML_NAME)

    @staticmethod
    def get_upgrade_meta_path(path):
        return os.path.join(path, Deploy.UPRADE_META_NAME)

    @staticmethod
    def get_inner_config_path(path):
        return os.path.join(path, Deploy.INNER_CONFIG_NAME)

    @staticmethod
    def get_temp_deploy_yaml_path(path):
        return os.path.join(path, 'tmp_%s' % Deploy.DEPLOY_YAML_NAME)

    @property
    def deploy_info(self):
        if self._info is None:
            try:
                path = self.get_deploy_file_path(self.config_dir)
                with open(path, 'rb') as f:
                    data = yaml.load(f)
                    self._info = DeployInfo(
                        data['name'],
                        getattr(DeployStatus, data['status'], DeployStatus.STATUS_CONFIGURED),
                        ConfigUtil.get_value_from_dict(data, 'components', OrderedDict()),
                        getattr(DeployConfigStatus, ConfigUtil.get_value_from_dict(data, 'config_status', '_'), DeployConfigStatus.UNCHNAGE),
                        ConfigUtil.get_value_from_dict(data, 'create_date', None),
                    )
            except:
                self._info = DeployInfo(self.name, DeployStatus.STATUS_CONFIGURED)
        return self._info

    def _load_deploy_config(self, path):
        yaml_loader = YamlLoader(stdio=self.stdio)
        deploy_config = DeployConfig(path, yaml_loader=yaml_loader, config_parser_manager=self.config_parser_manager, stdio=self.stdio)
        deploy_info = self.deploy_info
        for component_name in deploy_info.components:
            if component_name not in deploy_config.components:
                continue
            config = deploy_info.components[component_name]
            cluster_config = deploy_config.components[component_name]
            if 'version' in config and config['version']:
                cluster_config.version = config['version']
            if 'hash' in config and config['hash']:
                cluster_config.package_hash = config['hash']
        deploy_config.inner_config = InnerConfig(self.get_inner_config_path(self.config_dir), yaml_loader=yaml_loader)
        return deploy_config

    @property
    def temp_deploy_config(self):
        path = self.get_temp_deploy_yaml_path(self.config_dir)
        return self._load_deploy_config(path)

    @property
    def deploy_config(self):
        if self._config is None:
            path = self.get_deploy_yaml_path(self.config_dir)
            self._config = self._load_deploy_config(path)
        return self._config

    def _get_uprade_meta(self):
        if self._uprade_meta is None and self.deploy_info.status == DeployStatus.STATUS_UPRADEING:
            try:
                path = self.get_upgrade_meta_path(self.config_dir)
                with open(path) as f:
                    self._uprade_meta = yaml.load(f)
            except:
                self.stdio and getattr(self.stdio, 'exception', print)('fail to load uprade meta data')
        return self._uprade_meta

    @property
    def upgrade_ctx(self):
        uprade_meta = self._get_uprade_meta()
        return uprade_meta.get('uprade_ctx') if uprade_meta else None

    @property
    def upgrading_component(self):
        uprade_meta = self._get_uprade_meta()
        return uprade_meta.get('component') if uprade_meta else None

    def apply_temp_deploy_config(self):
        self.stdio and getattr(self.stdio, 'verbose', print)('%s apply temp config' % self.name)
        src_yaml_path = self.get_temp_deploy_yaml_path(self.config_dir)
        target_src_path = self.get_deploy_yaml_path(self.config_dir)
        try:
            FileUtil.move(src_yaml_path, target_src_path)
            self._config = None
            self.update_deploy_config_status(DeployConfigStatus.UNCHNAGE)
            return True
        except Exception as e:
            self.stdio and getattr(self.stdio, 'exception', print)('mv %s to %s failed, error: \n%s' % (src_yaml_path, target_src_path, e))
        return False

    def dump_deploy_info(self):
        path = self.get_deploy_file_path(self.config_dir)
        self.stdio and getattr(self.stdio, 'verbose', print)('dump deploy info to %s' % path)
        try:
            with open(path, 'w') as f:
                data = {
                    'name': self.deploy_info.name,
                    'components': self.deploy_info.components,
                    'status': self.deploy_info.status.name,
                    'config_status': self.deploy_info.config_status.name,
                    'create_date': self.deploy_info.create_date,
                }
                yaml.dump(data, f)
            return True
        except:
            self.stdio and getattr(self.stdio, 'exception', print)('dump deploy info to %s failed' % path)
        return False

    def _update_deploy_status(self, status):
        old = self.deploy_info.status
        self.deploy_info.status = status
        if old == DeployStatus.STATUS_DEPLOYED and status == DeployStatus.STATUS_RUNNING:
            self.deploy_info.create_date = datetime.now().strftime('%Y-%m-%d')
        if self.dump_deploy_info():
            return True
        self.deploy_info.status = old
        return False

    def _update_deploy_config_status(self, status):
        old = self.deploy_info.config_status
        self.deploy_info.config_status = status
        if self.dump_deploy_info():
            return True
        self.deploy_info.config_status = old
        return False

    def _dump_upgrade_meta_data(self):
        path = self.get_upgrade_meta_path(self.config_dir)
        self.stdio and getattr(self.stdio, 'verbose', print)('dump upgrade meta data to %s' % path)
        try:
            if self._uprade_meta:
                with open(path, 'wb') as f:
                    yaml.dump(self._uprade_meta, f)
            else:
                FileUtil.rm(path, self.stdio)
            return True
        except:
            self.stdio and getattr(self.stdio, 'exception', print)('dump upgrade meta data to %s failed' % path)
        return False

    def start_upgrade(self, component, **uprade_ctx):
        if self.deploy_info.status != DeployStatus.STATUS_RUNNING:
            return False
        self._uprade_meta = {
            'component': component,
            'uprade_ctx': uprade_ctx
        }
        if self._dump_upgrade_meta_data() and self._update_deploy_status(DeployStatus.STATUS_UPRADEING):
            return True
        self._uprade_meta = None
        return False

    def update_upgrade_ctx(self, **uprade_ctx):
        if self.deploy_info.status != DeployStatus.STATUS_UPRADEING:
            return False
        uprade_meta = deepcopy(self._get_uprade_meta())
        self._uprade_meta['uprade_ctx'].update(uprade_ctx)
        if self._dump_upgrade_meta_data():
            return True
        self._uprade_meta = uprade_meta
        return False

    def update_component_repository(self, repository):
        if not self.deploy_config.update_component_info(repository):
            return False
        self.use_model(repository.name, repository)
        return True

    def stop_upgrade(self, dest_repository=None):
        if self._update_deploy_status(DeployStatus.STATUS_RUNNING):
            self._uprade_meta = None
            self._dump_upgrade_meta_data()
            if dest_repository:
                self.update_component_repository(dest_repository)
            return True
        return False

    def update_deploy_status(self, status):
        if isinstance(status, DeployStatus):
            if self._update_deploy_status(status):
                if DeployStatus.STATUS_DESTROYED == status:
                    self.deploy_info.components = {}
                    self.dump_deploy_info()
                return True
        return False

    def update_deploy_config_status(self, status):
        if isinstance(status, DeployConfigStatus):
            return self._update_deploy_config_status(status)
        return False

    def effect_tip(self):
        cmd_map = {
            DeployConfigStatus.NEED_RELOAD: 'obd cluster reload %s' % self.name,
            DeployConfigStatus.NEED_RESTART: 'obd cluster restart %s --wp' % self.name,
            DeployConfigStatus.NEED_REDEPLOY: 'obd cluster redeploy %s' % self.name,
        }
        if self.deploy_info.config_status in cmd_map:
            return '\nUse `%s` to make changes take effect.' % cmd_map[self.deploy_info.config_status]
        return ''


class ConfigParserManager(Manager):

    RELATIVE_PATH = 'config_parser/'

    def __init__(self, home_path, stdio=None):
        super(ConfigParserManager, self).__init__(home_path, stdio)
        self.global_parsers = {
            'default': DefaultConfigParser,
        }
        self.component_parsers = {}

    def _format_paraser_name(self, style):
        style = style.title()
        return '%sConfigParser' % style.replace('-', '').replace(' ', '').replace('_', '')

    def _load_paraser(self, lib_path, style):
        from tool import DynamicLoading
        module_name = '%s_config_parser' % style
        file_name = '%s.py' % module_name
        path = os.path.join(lib_path, file_name)
        if os.path.isfile(path):
            DynamicLoading.add_lib_path(lib_path)
            self.stdio and getattr(self.stdio, 'verbose', 'print')('load config parser: %s' % path)
            module = DynamicLoading.import_module(module_name, self.stdio)
            clz_name = self._format_paraser_name(style)
            try:
                return getattr(module, clz_name)
            except:
                self.stdio and getattr(self.stdio, 'exception', 'print')('')
                return None
            finally:
                DynamicLoading.remove_lib_path(lib_path)
        else:
            self.stdio and getattr(self.stdio, 'verbose', 'print')('No config parser: %s' % path)
            return None

    def _get_component_parser(self, component, style):
        if component not in self.component_parsers:
            self.component_parsers[component] = {}
        component_parsers = self.component_parsers[component]
        if style not in component_parsers:
            lib_path = os.path.join(self.path, component)
            component_parsers[style] = self._load_paraser(lib_path, style)
        return component_parsers[style]

    def _get_global_parser(self, style):
        if style not in self.global_parsers:
            self.global_parsers[style] = self._load_paraser(self.path, style)
        return self.global_parsers[style]

    def get_parser(self, component='', style=''):
        if not style or style == 'default':
            return self.global_parsers['default']
        if component:
            parser = self._get_component_parser(component, style)
            if parser:
                return parser
        parser = self._get_global_parser(style)
        if not parser:
            raise ParserError('Unsupported configuration style: %s %s' % (component, style))
        return parser


class DeployManager(Manager):

    RELATIVE_PATH = 'cluster/'
    
    def __init__(self, home_path, lock_manager=None, stdio=None):
        super(DeployManager, self).__init__(home_path, stdio)
        self.lock_manager = lock_manager
        self.config_parser_manager = ConfigParserManager(home_path, stdio)

    def _lock(self, name, read_only=False):
        if self.lock_manager:
            if read_only:
                return self.lock_manager.deploy_sh_lock(name)
            else:
                return self.lock_manager.deploy_ex_lock(name)
        return True

    def get_deploy_configs(self, read_only=True):
        configs = []
        for name in os.listdir(self.path):
            path = os.path.join(self.path, name)
            if os.path.isdir(path):
                self._lock(name, read_only)
                configs.append(Deploy(path, config_parser_manager=self.config_parser_manager, stdio=self.stdio))
        return configs

    def get_deploy_config(self, name, read_only=False):
        self._lock(name, read_only)
        path = os.path.join(self.path, name)
        if os.path.isdir(path):
            return Deploy(path, config_parser_manager=self.config_parser_manager, stdio=self.stdio)
        return None

    def create_deploy_config(self, name, src_yaml_path):
        self._lock(name)
        config_dir = os.path.join(self.path, name)
        target_src_path = Deploy.get_deploy_yaml_path(config_dir)
        self._mkdir(config_dir)
        if FileUtil.copy(src_yaml_path, target_src_path, self.stdio):
            return Deploy(config_dir, config_parser_manager=self.config_parser_manager, stdio=self.stdio)
        else:
            self._rm(config_dir)
            return None
        
    def remove_deploy_config(self, name):
        self._lock(name)
        config_dir = os.path.join(self.path, name)
        self._rm(config_dir)
