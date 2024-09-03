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
import sys
import time
import inspect2
from enum import Enum
from glob import glob
from copy import deepcopy, copy

from _manager import Manager
from _rpm import Version, get_prefix_version, add_sub_version
from ssh import ConcurrentExecutor
from tool import ConfigUtil, DynamicLoading, YamlLoader, FileUtil
from _types import *


yaml = YamlLoader()


class PluginType(Enum):

    # 插件类型 = 插件加载类
    START = 'StartPlugin'
    PARAM = 'ParamPlugin'
    INSTALL = 'InstallPlugin'
    SNAP_CONFIG = 'SnapConfigPlugin'
    PY_SCRIPT = 'PyScriptPlugin'


class Plugin(object):

    PLUGIN_TYPE = None
    FLAG_FILE = None

    def __init__(self, component_name, plugin_path, version, dev_mode):
        if not self.PLUGIN_TYPE or not self.FLAG_FILE:
            raise NotImplementedError
        self.component_name = component_name
        self.plugin_path = plugin_path
        self.version = Version(version)
        self.dev_mode = dev_mode

    def __str__(self):
        return '%s-%s-%s' % (self.component_name, self.PLUGIN_TYPE.name.lower(), self.version)

    @property
    def mirror_type(self):
        return self.PLUGIN_TYPE


class PluginContextNamespace:

    def __init__(self, spacename):
        self.spacename = spacename
        self._variables = {}
        self._return = {}

    @property
    def variables(self):
        return self._variables

    def get_variable(self, name, default=None):
        return self._variables.get(name, default)

    def set_variable(self, name, value):
        self._variables[name] = value

    def get_return(self, plugin_name):
        ret = self._return.get(plugin_name)
        if isinstance(ret, PluginReturn):
            return ret
        return PluginReturn()

    def set_return(self, plugin_name, plugin_return):
        self._return[plugin_name] = plugin_return


class PluginReturn(object):

    def __init__(self, value=None, *arg, **kwargs):
        self._return_value = value
        self._return_args = arg
        self._return_kwargs = kwargs

    def __nonzero__(self):
        return self.__bool__()

    def __bool__(self):
        return True if self._return_value else False

    @property
    def value(self):
        return self._return_value

    @property
    def args(self):
        return self._return_args

    @property
    def kwargs(self):
        return self._return_kwargs

    def get_return(self, key, default=None):
        return self.kwargs.get(key, default)

    def set_args(self, *args):
        self._return_args = args

    def set_kwargs(self, **kwargs):
        self._return_kwargs = kwargs

    def set_return(self, value):
        self._return_value = value

    def return_true(self, *args, **kwargs):
        self.set_return(True)
        self.set_args(*args)
        self.set_kwargs(**kwargs)

    def return_false(self, *args, **kwargs):
        self.set_return(False)
        self.set_args(*args)
        self.set_kwargs(**kwargs)


class PluginContext(object):

    def __init__(self, plugin_name, namespace, namespaces, deploy_name, deploy_status, repositories, components, clients, cluster_config, cmd, options, dev_mode, stdio):
        self.namespace = namespace
        self.namespaces = namespaces
        self.deploy_name  = deploy_name
        self.deploy_status  = deploy_status
        self.repositories =repositories
        self.plugin_name = plugin_name
        self.components = components
        self.clients = clients
        self.cluster_config = cluster_config
        self.cmds = cmd
        self.options = options
        self.dev_mode = dev_mode
        self.stdio = stdio
        self.concurrent_executor = ConcurrentExecutor(32)
        self._return = PluginReturn()

    def get_return(self, plugin_name=None, spacename=None):
        if spacename:
            namespace = self.namespaces.get(spacename)
        else:
            namespace = self.namespace
        if plugin_name is None:
            plugin_name = self.plugin_name
        return namespace.get_return(plugin_name) if namespace else None

    def return_true(self, *args, **kwargs):
        self._return.return_true(*args, **kwargs)
        self.namespace.set_return(self.plugin_name, self._return)

    def return_false(self, *args, **kwargs):
        self._return.return_false(*args, **kwargs)
        self.namespace.set_return(self.plugin_name, self._return)

    def get_variable(self, name, spacename=None, default=None):
        if spacename:
            namespace = self.namespaces.get(spacename)
        else:
            namespace = self.namespace
        return namespace.get_variable(name, default) if namespace else None

    def set_variable(self, name, value):
        self.namespace.set_variable(name, value)


class SubIO(object):

    def __init__(self, stdio):
        self.stdio = getattr(stdio, 'sub_io', lambda: None)()
        self._func = {}

    def __del__(self):
        self.before_close()

    def _temp_function(self, *arg, **kwargs):
        pass

    def __getattr__(self, name):
        if name not in self._func:
            self._func[name] = getattr(self.stdio, name, self._temp_function)
        return self._func[name]


class ScriptPlugin(Plugin):

    class ClientForScriptPlugin(object):

        def __init__(self, client, stdio):
            self.client = client
            self.stdio = stdio

        def __getattr__(self, key):
            def new_method(*args, **kwargs):
                if "stdio" not in kwargs:
                    kwargs['stdio'] = self.stdio
                return attr(*args, **kwargs)
            attr = getattr(self.client, key)
            if hasattr(attr, '__call__'):
                return new_method
            return attr

    def __init__(self, component_name, plugin_path, version, dev_mode):
        super(ScriptPlugin, self).__init__(component_name, plugin_path, version, dev_mode)
        self.context = None

    def __call__(self):
        raise NotImplementedError

    def _import(self, stdio=None):
        raise NotImplementedError

    def _export(self):
        raise NotImplementedError

    def __del__(self):
        self._export()

    def before_do(
        self, plugin_name, namespace, namespaces, deploy_name, deploy_status,
        repositories, components, clients, cluster_config, cmd,
        options, stdio, *arg, **kwargs
        ):
        self._import(stdio)
        sub_stdio = SubIO(stdio)
        sub_clients = {}
        for server in clients:
            sub_clients[server] = ScriptPlugin.ClientForScriptPlugin(clients[server], sub_stdio)
        self.context = PluginContext(
            plugin_name, namespace, namespaces, deploy_name, deploy_status, repositories, components,
            sub_clients, cluster_config, cmd, options, self.dev_mode, sub_stdio
        )
        namespace.set_return(plugin_name, None)

    def after_do(self, stdio, *arg, **kwargs):
        self._export(stdio)
        self.context = None


def pyScriptPluginExec(func):
    def _new_func(
        self, namespace, namespaces, deploy_name, deploy_status,
        repositories, components, clients, cluster_config, cmd,
        options, stdio, *arg, **kwargs
        ):
        self.before_do(self.name, namespace, namespaces, deploy_name, deploy_status,
        repositories, components, clients, cluster_config, cmd,
        options, stdio, *arg, **kwargs)
        method_name = self.PLUGIN_NAME
        run_result = self.context.get_variable('run_result', default={})
        run_result[method_name] = {'result': True}
        start_time = time.time()
        if self.module:
            method = getattr(self.module, method_name, False)
            namespace_vars = copy(self.context.namespace.variables)
            namespace_vars.update(kwargs)
            if arg:
                idx = 0
                params = list(inspect2.signature(method).parameters.keys())[1:-2]
                num = min(len(arg), len(params))
                while idx < num:
                    key = params[idx]
                    if key in namespace_vars:
                        del namespace_vars[key]
                    idx += 1
            kwargs = namespace_vars
            if method:
                target_servers = None
                if cluster_config:
                    servers = cluster_config.servers
                    target_servers = kwargs.get('target_servers')
                    if target_servers is not None:
                        cluster_config.servers = target_servers
                        stdio and getattr(stdio, 'verbose', print)('plugin %s target_servers: %s' % (self, target_servers))
                        del kwargs['target_servers']
                try:
                    ret = method(self.context, *arg, **kwargs)
                    if ret is None and self.context and self.context.get_return() is None:
                        run_result[method_name]['result'] = False
                        self.context.return_false()
                except Exception as e:
                    run_result[method_name]['result'] = False
                    self.context.return_false(exception=e)
                    stdio and getattr(stdio, 'exception', print)('%s RuntimeError: %s' % (self, e))
                finally:
                    if target_servers:
                        cluster_config.servers = servers
                        stdio and getattr(stdio, 'verbose', print)('plugin %s restore servers: %s' % (self, servers))
        end_time = time.time()
        run_result[method_name]['time'] = end_time - start_time
        self.context.set_variable('run_result', run_result)
        ret = self.context.get_return() if self.context else PluginReturn()
        self.after_do(stdio, *arg, **kwargs)
        stdio and getattr(stdio, 'verbose', print)('plugin %s result: %s' % (self, ret.value))
        return ret
    return _new_func


class PyScriptPlugin(ScriptPlugin):

    LIBS_PATH = []
    PLUGIN_NAME = None

    def __init__(self, component_name, plugin_path, version, dev_mode):
        if not self.PLUGIN_NAME:
            raise NotImplementedError
        super(PyScriptPlugin, self).__init__(component_name, plugin_path, version, dev_mode)
        self.module = None
        self.name = self.PLUGIN_NAME
        self.libs_path = deepcopy(self.LIBS_PATH)
        self.libs_path.append(self.plugin_path)

    def __call__(
        self, namespace, namespaces, deploy_name, deploy_status,
        repositories, components, clients, cluster_config, cmd,
        options, stdio, *arg, **kwargs
        ):
        method = getattr(self, self.PLUGIN_NAME, False)
        if method:
            return method(
                namespace, namespaces, deploy_name, deploy_status,
                repositories, components, clients, cluster_config, cmd,
                options, stdio, *arg, **kwargs
            )
        else:
            raise NotImplementedError

    def _import(self, stdio=None):
        if self.module is None:
            DynamicLoading.add_libs_path(self.libs_path)
            self.module = DynamicLoading.import_module(self.PLUGIN_NAME, stdio)

    def _export(self, stdio=None):
        if self.module:
            DynamicLoading.remove_libs_path(self.libs_path)
            DynamicLoading.export_module(self.PLUGIN_NAME, stdio)

# this is PyScriptPlugin demo
# class InitPlugin(PyScriptPlugin):

#     FLAG_FILE = 'init.py'
#     PLUGIN_NAME = 'init'
#     PLUGIN_TYPE = PluginType.INIT

#     def __init__(self, component_name, plugin_path, version):
#         super(InitPlugin, self).__init__(component_name, plugin_path, version)

#     @pyScriptPluginExec
#     def init(
#         self, namespace, namespaces, deploy_name,
#         repositories, components, clients, cluster_config, cmd,
#         options, stdio, *arg, **kwargs):
#         pass

class Null(object):

    def __init__(self):
        pass

class ParamPlugin(Plugin):


    class ConfigItem(object):

        def __init__(
            self,
            name,
            param_type=str,
            default=None,
            min_value=None,
            max_value=None,
            require=False,
            essential=False,
            section="",
            need_reload=False,
            need_restart=False,
            need_redeploy=False,
            modify_limit=None,
            name_local=None,
            description_en=None,
            description_local=None
        ):
            self.name = name
            self.default = default
            self.require = require
            self.essential = essential
            self.section = section
            self.need_reload = need_reload
            self.need_restart = need_restart
            self.need_redeploy = need_redeploy
            self._param_type = param_type
            self.min_value = param_type(min_value) if min_value is not None else None
            self.max_value = param_type(max_value) if max_value is not None else None
            self.modify_limit = getattr(self, ('_%s_limit' % modify_limit).lower(), self._none_limit)
            self.had_modify_limit = self.modify_limit != self._none_limit
            self.name_local = name_local if name_local is not None else self.name
            self.description_en = description_en
            self.description_local = description_local if description_local is not None else self.description_en

        def param_type(self, value):
            try:
                return self._param_type(value)
            except Exception as e:
                raise Exception('%s: %s' % (self.name, e))

        def check_value(self, value):
            if not isinstance(value, self._param_type):
                value = self.param_type(value)
            if self.min_value is not None and value < self.min_value:
                raise Exception('%s less then %s' % (self.name, self.min_value))
            if self.max_value is not None and value > self.max_value:
                raise Exception('%s more then %s' % (self.name, self.max_value))
            return True

        def _modify_limit(self, old_value, new_value):
            if old_value == new_value:
                return True
            raise Exception('DO NOT modify %s after startup' % self.name)

        def _increase_limit(self, old_value, new_value):
            if self.param_type(new_value) > self.param_type(old_value):
                raise Exception('DO NOT increase %s after startup' % self.name)
            return True

        def _decrease_limit(self, old_value, new_value):
            if self.param_type(new_value) < self.param_type(old_value):
                raise Exception('DO NOT decrease %s after startup' % self.name)
            return True

        def _none_limit(self, old_value, new_value):
            return True

    PLUGIN_TYPE = PluginType.PARAM
    DEF_PARAM_YAML = 'parameter.yaml'
    FLAG_FILE = DEF_PARAM_YAML

    def __init__(self, component_name, plugin_path, version, dev_mode):
        super(ParamPlugin, self).__init__(component_name, plugin_path, version, dev_mode)
        self.def_param_yaml_path = os.path.join(self.plugin_path, self.DEF_PARAM_YAML)
        self._src_data = None
        self._need_redploy_items = None
        self._had_modify_limit_items = None
        self._need_restart_items = None
        self._params_default = None

    @property
    def params(self):
        if self._src_data is None:
            try:
                TYPES = {
                    'DOUBLE': Double,
                    'BOOL': Boolean,
                    'INT': Integer,
                    'STRING': String,
                    'PATH': Path,
                    'PATH_LIST': PathList,
                    'SAFE_STRING': SafeString,
                    'SAFE_STRING_LIST': SafeStringList,
                    'MOMENT': Moment,
                    'TIME': Time,
                    'CAPACITY': Capacity,
                    'CAPACITY_MB': CapacityMB,
                    'STRING_LIST': StringList,
                    'DICT': Dict,
                    'LIST': List,
                    'PARAM_LIST': StringOrKvList,
                    'DB_URL': DBUrl,
                    'WEB_URL': WebUrl,
                    'OB_USER': OBUser
                }
                self._src_data = {}
                with open(self.def_param_yaml_path, 'rb') as f:
                    configs = yaml.load(f)
                    for conf in configs:
                        try:
                            param_type = ConfigUtil.get_value_from_dict(conf, 'type', 'STRING').upper()
                            if param_type in TYPES:
                                param_type = TYPES[param_type]
                            else:
                                param_type = String

                            self._src_data[conf['name']] = ParamPlugin.ConfigItem(
                                name=conf['name'],
                                param_type=param_type,
                                default=ConfigUtil.get_value_from_dict(conf, 'default', None),
                                min_value=ConfigUtil.get_value_from_dict(conf, 'min_value', None),
                                max_value=ConfigUtil.get_value_from_dict(conf, 'max_value', None),
                                modify_limit=ConfigUtil.get_value_from_dict(conf, 'modify_limit', None),
                                require=ConfigUtil.get_value_from_dict(conf, 'require', False),
                                section=ConfigUtil.get_value_from_dict(conf, 'section', ""),
                                essential=ConfigUtil.get_value_from_dict(conf, 'essential', False),
                                need_reload=ConfigUtil.get_value_from_dict(conf, 'need_reload', False),
                                need_restart=ConfigUtil.get_value_from_dict(conf, 'need_restart', False),
                                need_redeploy=ConfigUtil.get_value_from_dict(conf, 'need_redeploy', False),
                                description_en=ConfigUtil.get_value_from_dict(conf, 'description_en', None),
                                description_local=ConfigUtil.get_value_from_dict(conf, 'description_local', None),
                            )
                        except:
                            pass
            except:
                pass
        return self._src_data

    @property
    def redploy_params(self):
        if self._need_redploy_items is None:
            self._need_redploy_items = []
            params = self.params
            for name in params:
                conf = params[name]
                if conf.need_redeploy:
                    self._need_redploy_items.append(conf)
        return self._need_redploy_items

    @property
    def modify_limit_params(self):
        if self._had_modify_limit_items is None:
            self._had_modify_limit_items = []
            params = self.params
            for name in params:
                conf = params[name]
                if conf.had_modify_limit:
                    self._had_modify_limit_items.append(conf)
        return self._had_modify_limit_items

    @property
    def restart_params(self):
        if self._need_restart_items is None:
            self._need_restart_items = []
            params = self.params
            for name in params:
                conf = params[name]
                if conf.need_restart:
                    self._need_restart_items.append(conf)
        return self._need_restart_items

    @property
    def params_default(self):
        if self._params_default is None:
            self._params_default = {}
            params = self.params
            for name in params:
                conf = params[name]
                self._params_default[conf.name] = conf.default
        return self._params_default


class SnapConfigPlugin(Plugin):

    PLUGIN_TYPE = PluginType.SNAP_CONFIG
    CONFIG_YAML = 'snap_config.yaml'
    FLAG_FILE = CONFIG_YAML
    _KEYCRE = re.compile(r"\$(\w+)")

    def __init__(self, component_name, plugin_path, version, dev_mode):
        super(SnapConfigPlugin, self).__init__(component_name, plugin_path, version, dev_mode)
        self.config_path = os.path.join(self.plugin_path, self.CONFIG_YAML)
        self._config = None
        self._file_hash = None

    def __hash__(self):
        if self._file_hash is None:
            self._file_hash = int(''.join(['%03d' % (ord(v) if isinstance(v, str) else v) for v in FileUtil.checksum(self.config_path)]))
        return self._file_hash

    @property
    def config(self):
        if self._config is None:
            with open(self.config_path, 'rb') as f:
                self._config = yaml.load(f)
        return self._config

    @property
    def backup(self):
        return self.config.get('backup', [])

    @property
    def clean(self):
        return self.config.get('clean', [])


class InstallPlugin(Plugin):

    class FileItemType(Enum):

        FILE = 0
        DIR = 1
        BIN = 2
        JAR = 3

    class InstallMethod(Enum):

        ANY = 0
        CP = 1

    class FileItem(object):

        def __init__(self, src_path, target_path, _type, install_method, require):
            self.src_path = src_path
            self.target_path = target_path
            self.type = _type if _type else InstallPlugin.FileItemType.FILE
            self.install_method = install_method or InstallPlugin.InstallMethod.ANY
            self.require = require
    
    class RequirementItem(object):

        def __init__(self, name, version, min_version, max_version):
            self.name = name
            self.version = version
            self.min_version = min_version
            self.max_version = max_version
            
        def __hash__(self):
            return hash(tuple(sorted(self.__dict__.items())))

        def __eq__(self, other):
            return self.__dict__ == other.__dict__

    PLUGIN_TYPE = PluginType.INSTALL
    FILES_MAP_YAML = 'file_map.yaml'
    FLAG_FILE = FILES_MAP_YAML
    REQUIREMENT_YAML = 'requirement.yaml'
    _KEYCRE = re.compile(r"\$(\w+)")
    _VERSION_KEYCRE = re.compile(r"\$version(\[(\d+)\])?")

    def __init__(self, component_name, plugin_path, version, dev_mode):
        super(InstallPlugin, self).__init__(component_name, plugin_path, version, dev_mode)
        self.file_map_path = os.path.join(self.plugin_path, self.FILES_MAP_YAML)
        self._file_map = {}
        self._file_map_data = None
        self._check_value = None
        self.requirement_path = os.path.join(self.plugin_path, self.REQUIREMENT_YAML)
        self._requirement = {}
        self._requirement_data = None

    @classmethod
    def var_replace(cls, string, var):
        if not var:
            return string
        done = []

        while string:
            m = cls._KEYCRE.search(string)
            if not m:
                done.append(string)
                break
            varname = m.group(1).lower()
            replacement = var.get(varname, m.group())

            start, end = m.span()
            done.append(string[:start])
            done.append(str(replacement))
            string = string[end:]

        return ''.join(done)

    @property
    def check_value(self):
        if self._check_value is None:
            self._check_value = os.path.getmtime(self.file_map_path)
        return self._check_value

    @property
    def file_map_data(self):
        if self._file_map_data is None:
            with open(self.file_map_path, 'rb') as f:
                self._file_map_data = yaml.load(f)
        return self._file_map_data
    
    @property
    def requirement_data(self):
        if self._requirement_data is None:
            if os.path.exists(self.requirement_path):
                with open(self.requirement_path, 'rb') as f:
                    self._requirement_data = yaml.load(f)
            else:
                self._requirement_data = {}
        return self._requirement_data

    def file_map(self, package_info):
        var = {
            'name': package_info.name,
            'version': package_info.version,
            'release': package_info.release,
            'release_simple': package_info.release.simple(),
            'arch': package_info.arch,
            'md5': package_info.md5,
        }
        key = str(var)
        if not self._file_map.get(key):
            try:
                file_map = {}
                for data in self.file_map_data:
                    k = data['src_path']
                    if k[0] != '.':
                        k = '.%s' % os.path.join('/', k)
                    k = self.var_replace(k, var)
                    file_map[k] = InstallPlugin.FileItem(
                        k,
                        ConfigUtil.get_value_from_dict(data, 'target_path', k),
                        getattr(InstallPlugin.FileItemType, ConfigUtil.get_value_from_dict(data, 'type', 'FILE').upper(), None),
                        getattr(InstallPlugin.InstallMethod, ConfigUtil.get_value_from_dict(data, 'install_method', 'ANY').upper(), None),
                        ConfigUtil.get_value_from_dict(data, 'require', None),
                    )
                self._file_map[key] = file_map
            except:
                pass
        return self._file_map[key]

    def file_list(self, package_info):
        file_map = self.file_map(package_info)
        return [file_map[k] for k in file_map]
    
    def version_replace(cls, string, main_componentt_version):
        """
        replace the version when configure the "$version" variable in requirement.yaml

        :param string: the "version config" from requirement.yaml
        :param main_componentt_version: the main component version
        :return: the replaced version and offset
        """
        if not main_componentt_version:
            return string, 0
        m = cls._VERSION_KEYCRE.search(string)
        if not m:
            return string, 0
        
        if not m.group(2):
            return main_componentt_version, 0
        
        return get_prefix_version(Version(main_componentt_version), m.group(2)), m.group(2)
    
    def requirement_map(self, package_info):
        var = {
            'name': package_info.name,
            'version': package_info.version,
            'release': package_info.release,
            'arch': package_info.arch,
            'md5': package_info.md5,
        }
        key = str(var)
        if not self._requirement.get(key):
            try:
                requirement_map = {}
                if self.requirement_data:
                    for component_name in self.requirement_data:
                        value = self.requirement_data[component_name]
                        # Once the version is configured and then obd find the package is equal to the version
                        version = ConfigUtil.get_value_from_dict(value, 'version', transform_func=Version)
                        min_version = max_version = None
                        if not version:
                            min_version = ConfigUtil.get_value_from_dict(value, 'min_version', transform_func=Version)
                            max_version = ConfigUtil.get_value_from_dict(value, 'max_version', transform_func=Version)
                        else:
                            version_replace, offset = self.version_replace(version, var['version'])
                            if version_replace != version:
                                if offset == 0:
                                    version = version_replace
                                else:
                                    version = None
                                    min_version = version_replace
                                    max_version = add_sub_version(Version(version_replace), offset, 1)
                        requirement_map[component_name] = InstallPlugin.RequirementItem(
                            component_name,
                            str(version) if version else None,
                            str(min_version) if min_version else None,
                            str(max_version) if max_version else None,
                        )
                self._requirement[key] = requirement_map
            except:
                pass
        return self._requirement[key]
        
    def requirement_list(self, package_info):
        requirement_map = self.requirement_map(package_info)
        return [requirement_map[k] for k in requirement_map]


class ComponentPluginLoader(object):

    PLUGIN_TYPE = None

    def __init__(self, home_path, plugin_type=PLUGIN_TYPE, dev_mode=False, stdio=None):
        if plugin_type:
            self.PLUGIN_TYPE = plugin_type
        if not self.PLUGIN_TYPE:
            raise NotImplementedError
        self.plguin_cls = getattr(sys.modules[__name__], self.PLUGIN_TYPE.value, False)
        if not self.plguin_cls:
            raise ImportError(self.PLUGIN_TYPE.value)
        self.dev_mode = dev_mode
        self.stdio = stdio
        self.path = home_path
        self.component_name = os.path.split(self.path)[1]
        self._plugins = {}

    def get_plugins(self):
        plugins = []
        for flag_path in glob('%s/*/%s' % (self.path, self.plguin_cls.FLAG_FILE)):
            if flag_path in self._plugins:
                plugins.append(self._plugins[flag_path])
            else:
                path, _ = os.path.split(flag_path)
                _, version = os.path.split(path)
                plugin = self.plguin_cls(self.component_name, path, version, self.dev_mode)
                self._plugins[flag_path] = plugin
                plugins.append(plugin)
        return plugins

    def get_best_plugin(self, version):
        version = Version(version)
        plugins = []
        for plugin in self.get_plugins():
            if plugin.version == version:
                return plugin
            if plugin.version < version:
                plugins.append(plugin)
        if plugins:
            plugin = max(plugins, key=lambda x: x.version)
            # self.stdio and getattr(self.stdio, 'warn', print)(
            #     '%s %s plugin version %s not found, use the best suitable version %s.\n Use `obd update` to update local plugin repository' %
            #     (self.component_name, self.PLUGIN_TYPE.name.lower(), version, plugin.version)
            #     )
            return plugin
        return None


class PyScriptPluginLoader(ComponentPluginLoader):

    class PyScriptPluginType(object):

        def __init__(self, name, value):
            self.name = name
            self.value = value

    PLUGIN_TYPE = PluginType.PY_SCRIPT

    def __init__(self, home_path, script_name=None, dev_mode=False, stdio=None):
        if not script_name:
            raise NotImplementedError
        type_name = 'PY_SCRIPT_%s' % script_name.upper()
        type_value = 'PyScript%sPlugin' % ''.join([word.capitalize() for word in script_name.split('_')])
        self.PLUGIN_TYPE = PyScriptPluginLoader.PyScriptPluginType(type_name, type_value)
        if not getattr(sys.modules[__name__], type_value, False):
            self._create_(script_name)
        super(PyScriptPluginLoader, self).__init__(home_path, dev_mode=dev_mode, stdio=stdio)

    def _create_(self, script_name):
        exec('''
class %s(PyScriptPlugin):

    FLAG_FILE = '%s.py'
    PLUGIN_NAME = '%s'

    def __init__(self, component_name, plugin_path, version, dev_mode):
        super(%s, self).__init__(component_name, plugin_path, version, dev_mode)

    @staticmethod
    def set_plugin_type(plugin_type):
        %s.PLUGIN_TYPE = plugin_type

    @pyScriptPluginExec
    def %s(
        self, namespace, namespaces, deploy_name, deploy_status,
        repositories, components, clients, cluster_config, cmd,
        options, stdio, *arg, **kwargs):
        pass
        ''' % (self.PLUGIN_TYPE.value, script_name, script_name, self.PLUGIN_TYPE.value, self.PLUGIN_TYPE.value, script_name))
        clz = locals()[self.PLUGIN_TYPE.value]
        setattr(sys.modules[__name__], self.PLUGIN_TYPE.value, clz)
        clz.set_plugin_type(self.PLUGIN_TYPE)
        return clz


class PluginManager(Manager):

    RELATIVE_PATH = 'plugins'
    # The directory structure for plugin is ./plugins/{component_name}/{version}

    def __init__(self, home_path, dev_mode=False, stdio=None):
        super(PluginManager, self).__init__(home_path, stdio=stdio)
        self.dev_mode = dev_mode
        self.component_plugin_loaders = {}
        self.py_script_plugin_loaders = {}
        for plugin_type in PluginType:
            self.component_plugin_loaders[plugin_type] = {}
        # PyScriptPluginLoader is a customized script loader. It needs special processing.
        # Log off the PyScriptPluginLoader in component_plugin_loaders
        del self.component_plugin_loaders[PluginType.PY_SCRIPT]

    def get_best_plugin(self, plugin_type, component_name, version):
        if plugin_type not in self.component_plugin_loaders:
            return None
        loaders = self.component_plugin_loaders[plugin_type]
        if component_name not in loaders:
            loaders[component_name] = ComponentPluginLoader(os.path.join(self.path, component_name), plugin_type, self.dev_mode, self.stdio)
        loader = loaders[component_name]
        return loader.get_best_plugin(version)

    # 主要用于获取自定义Python脚本插件
    # 相比于get_best_plugin，该方法可以获取到未在PluginType中注册的Python脚本插件
    # 这个功能可以快速实现自定义插件，只要在插件仓库创建对应的python文件，并暴露出同名方法即可
    # 使后续进一步实现全部流程可描述更容易实现
    def get_best_py_script_plugin(self, script_name, component_name, version):
        if script_name not in self.py_script_plugin_loaders:
            self.py_script_plugin_loaders[script_name] = {}
        loaders = self.py_script_plugin_loaders[script_name]
        if component_name not in loaders:
            loaders[component_name] = PyScriptPluginLoader(os.path.join(self.path, component_name), script_name, self.dev_mode, self.stdio)
        loader = loaders[component_name]
        return loader.get_best_plugin(version)
