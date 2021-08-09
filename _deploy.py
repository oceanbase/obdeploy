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

import os
import re
import getpass
from copy import deepcopy
from enum import Enum

from tool import ConfigUtil, FileUtil, YamlLoader
from _manager import Manager
from _repository import Repository


yaml = YamlLoader()


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


class ServerConfig(object):

    def __init__(self, ip, name=None):
        self.ip = ip
        self._name = name

    @property
    def name(self):
        return self._name if self._name else self.ip

    def __str__(self):
        return '%s(%s)' % (self._name, self.ip) if self._name else self.ip

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


class ClusterConfig(object):

    def __init__(self, servers, name, version, tag, package_hash):
        self.version = version
        self.tag = tag
        self.name = name
        self.origin_package_hash = package_hash
        self.package_hash = package_hash
        self._temp_conf = {}
        self._default_conf = {}
        self._global_conf = {}
        self._server_conf = {}
        self._cache_server = {}
        self.servers = servers
        for server in servers:
            self._server_conf[server] = {}
            self._cache_server[server] = None
        self._deploy_config = None

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self._global_conf == other._global_conf and self._server_conf == other._server_conf

    def set_deploy_config(self, _deploy_config):
        if self._deploy_config is None:
            self._deploy_config = _deploy_config
            return True
        return False
        
    def update_server_conf(self, server, key, value, save=True):
        if self._deploy_config is None:
            return False
        if not self._deploy_config.update_component_server_conf(self.name, server, key, value, save):
            return False
        self._server_conf[server][key] = value
        if self._cache_server[server] is not None:
            self._cache_server[server][key] = value
        return True

    def update_global_conf(self, key, value, save=True):
        if self._deploy_config is None:
            return False
        if not self._deploy_config.update_component_global_conf(self.name, key, value, save):
            return False
        self._global_conf[key] = value
        for server in self._cache_server:
            if self._cache_server[server] is not None:
                self._cache_server[server][key] = value
        return True

    def get_unconfigured_require_item(self, server):
        items = []
        config = self.get_server_conf(server)
        for key in self._temp_conf:
            if not self._temp_conf[key].require:
                continue
            if key in config:
                continue
            items.append(key)
        return items

    def get_server_conf_with_default(self, server):
        config = {}
        for key in self._temp_conf:
            if self._temp_conf[key].default is not None:
                config[key] = self._temp_conf[key].default
        config.update(self.get_server_conf(server))
        return config

    def get_need_redeploy_items(self, server):
        items = {}
        config = self.get_server_conf(server)
        for key in config:
            if key in self._temp_conf and self._temp_conf[key].need_redeploy:
                items[key] = config[key]
        return items

    def get_need_restart_items(self, server):
        items = {}
        config = self.get_server_conf(server)
        for key in config:
            if key in self._temp_conf and self._temp_conf[key].need_restart:
                items[key] = config[key]
        return items
        
    def update_temp_conf(self, temp_conf):
        self._default_conf = {}
        self._temp_conf = temp_conf
        for key in self._temp_conf:
            if self._temp_conf[key].require and self._temp_conf[key].default is not None:
                self._default_conf[key] = self._temp_conf[key].default
        self.set_global_conf(self._global_conf) # 更新全局配置

    def set_global_conf(self, conf):
        self._global_conf = deepcopy(self._default_conf)
        self._global_conf.update(conf)
        for server in self._cache_server:
            self._cache_server[server] = None

    def add_server_conf(self, server, conf):
        if server not in self.servers:
            self.servers.append(server)
        self._server_conf[server] = conf
        self._cache_server[server] = None

    def get_global_conf(self):
        return self._global_conf

    def get_server_conf(self, server):
        if server not in self._server_conf:
            return None
        if self._cache_server[server] is None:
            conf = deepcopy(self._global_conf)
            conf.update(self._server_conf[server])
            self._cache_server[server] = conf
        return self._cache_server[server]

    def get_original_server_conf(self, server):
        return self._server_conf.get(server)


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


class DeployConfigStatus(Enum):

    UNCHNAGE = 'unchange'
    NEED_RELOAD = 'need reload'
    NEED_RESTART = 'need restart'
    NEED_REDEPLOY = 'need redeploy'


class DeployInfo(object):

    def __init__(self, name, status, components={}, config_status=DeployConfigStatus.UNCHNAGE):
        self.status = status
        self.name = name
        self.components = components
        self.config_status = config_status

    def __str__(self):
        info = ['%s (%s)' % (self.name, self.status.value)]
        for name in self.components:
            info.append('%s-%s' % (name, self.components[name]))
        return '\n'.join(info)


class DeployConfig(object):

    def __init__(self, yaml_path, yaml_loader=yaml):
        self._user = None
        self.unuse_lib_repository = False
        self.auto_create_tenant = False
        self.components = {}
        self._src_data = None
        self.yaml_path = yaml_path
        self.yaml_loader = yaml_loader
        self._load()

    @property
    def user(self):
        return self._user

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

    def _load(self):
        try:
            with open(self.yaml_path, 'rb') as f:
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
        except:
            pass
        if not self.user:
            self.set_user_conf(UserConfig())

    def _dump(self):
        try:
            with open(self.yaml_path, 'w') as f:
                self.yaml_loader.dump(self._src_data, f)
            return True
        except:
            pass
        return False

    def dump(self):
        return self._dump()

    def set_user_conf(self, conf):
        self._user = conf

    def update_component_server_conf(self, component_name, server, key, value, save=True):
        if component_name not in self.components:
            return False
        cluster_config = self.components[component_name]
        if server not in cluster_config.servers:
            return False
        component_config = self._src_data[component_name]
        if server.name not in component_config:
            component_config[server.name] = {key: value}
        else:
            component_config[server.name][key] = value
        return self.dump() if save else True

    def update_component_global_conf(self, component_name, key, value, save=True):
        if component_name not in self.components:
            return False
        component_config = self._src_data[component_name]
        if 'global' not in component_config:
            component_config['global'] = {key: value}
        else:
            component_config['global'][key] = value
        return self.dump() if save else True

    def _add_component(self, component_name, conf):
        if 'servers' in conf and isinstance(conf['servers'], list):
            servers = []
            for server in conf['servers']:
                if isinstance(server, dict):
                    ip = ConfigUtil.get_value_from_dict(server, 'ip', transform_func=str)
                    name = ConfigUtil.get_value_from_dict(server, 'name', transform_func=str)
                else:
                    ip = server
                    name = None
                if not re.match('^\d{1,3}(\\.\d{1,3}){3}$', ip):
                    continue
                server = ServerConfigFlyweightFactory.get_instance(ip, name)
                if server not in servers:
                    servers.append(server)
        else:
            servers = []
        cluster_conf = ClusterConfig(
            servers,
            component_name,
            ConfigUtil.get_value_from_dict(conf, 'version', None, str),
            ConfigUtil.get_value_from_dict(conf, 'tag', None, str),
            ConfigUtil.get_value_from_dict(conf, 'package_hash', None, str)
        )
        if 'global' in conf:
            cluster_conf.set_global_conf(conf['global'])
        for server in servers:
            if server.name in conf:
                cluster_conf.add_server_conf(server, conf[server.name])
        cluster_conf.set_deploy_config(self)
        self.components[component_name] = cluster_conf


class Deploy(object):

    DEPLOY_STATUS_FILE = '.data'
    DEPLOY_YAML_NAME = 'config.yaml'

    def __init__(self, config_dir, stdio=None):
        self.config_dir = config_dir
        self.name = os.path.split(config_dir)[1]
        self._info = None
        self._config = None
        self.stdio = stdio

    def use_model(self, name, repository, dump=True):
        self.deploy_info.components[name] = {
            'hash': repository.hash,
            'version': repository.version,
        }
        return self._dump_deploy_info() if dump else True

    @staticmethod
    def get_deploy_file_path(path):
        return os.path.join(path, Deploy.DEPLOY_STATUS_FILE)

    @staticmethod
    def get_deploy_yaml_path(path):
        return os.path.join(path, Deploy.DEPLOY_YAML_NAME)

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
                        ConfigUtil.get_value_from_dict(data, 'components', {}),
                        getattr(DeployConfigStatus, ConfigUtil.get_value_from_dict(data, 'config_status', '_'), DeployConfigStatus.UNCHNAGE),
                    )
            except:
                self._info = DeployInfo(self.name, DeployStatus.STATUS_CONFIGURED)
        return self._info

    @property
    def deploy_config(self):
        if self._config is None:
            try:
                path = self.get_deploy_yaml_path(self.config_dir)
                self._config = DeployConfig(path, YamlLoader(stdio=self.stdio))
                deploy_info = self.deploy_info
                for component_name in deploy_info.components:
                    if component_name not in self._config.components:
                        continue
                    config = deploy_info.components[component_name]
                    cluster_config = self._config.components[component_name]
                    if 'version' in config and config['version']:
                        cluster_config.version = config['version']
                    if 'hash' in config and config['hash']:
                        cluster_config.package_hash = config['hash']
            except:
                pass
        return self._config

    def apply_temp_deploy_config(self):
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

    def _dump_deploy_info(self):
        path = self.get_deploy_file_path(self.config_dir)
        self.stdio and getattr(self.stdio, 'verbose', print)('dump deploy info to %s' % path)
        try:
            with open(path, 'w') as f:
                data = {
                    'name': self.deploy_info.name,
                    'components': self.deploy_info.components,
                    'status': self.deploy_info.status.name,
                    'config_status': self.deploy_info.config_status.name,
                }
                yaml.dump(data, f)
            return True
        except:
            self.stdio and getattr(self.stdio, 'exception', print)('dump deploy info to %s failed' % path)
        return False

    def update_deploy_status(self, status):
        if isinstance(status, DeployStatus):
            self.deploy_info.status = status
            if DeployStatus.STATUS_DESTROYED == status:
                self.deploy_info.components = {}
            return self._dump_deploy_info()
        return False

    def update_deploy_config_status(self, status):
        if isinstance(status, DeployConfigStatus):
            self.deploy_info.config_status = status
            return self._dump_deploy_info()
        return False


class DeployManager(Manager):

    RELATIVE_PATH = 'cluster/'
    
    def __init__(self, home_path, stdio=None):
        super(DeployManager, self).__init__(home_path, stdio)

    def get_deploy_configs(self):
        configs = []
        for file_name in os.listdir(self.path):
            path = os.path.join(self.path, file_name)
            if os.path.isdir(path):
                configs.append(Deploy(path, self.stdio))
        return configs

    def get_deploy_config(self, name):
        path = os.path.join(self.path, name)
        if os.path.isdir(path):
            return Deploy(path, self.stdio)
        return None

    def create_deploy_config(self, name, src_yaml_path):
        config_dir = os.path.join(self.path, name)
        target_src_path = Deploy.get_deploy_yaml_path(config_dir)
        self._mkdir(config_dir)
        if FileUtil.copy(src_yaml_path, target_src_path, self.stdio):
            return Deploy(config_dir, self.stdio)
        else:
            self._rm(config_dir)
            return None
        
    def remove_deploy_config(self, name):
        config_dir = os.path.join(self.path, name)
        self._rm(config_dir)
