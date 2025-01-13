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

import enum
import os

from _manager import Manager
from _rpm import Version
from tool import YamlLoader, FileUtil, DynamicLoading

yaml_loader = YamlLoader()


class OptimizeManager(Manager):

    RELATIVE_PATH = "optimize/"

    def __init__(self, home_path, loader=yaml_loader, stdio=None):
        self.loader = loader
        self.components = {}
        self._parser = None
        self._optimize_config = None
        super(OptimizeManager, self).__init__(home_path, stdio=stdio)

    @property
    def optimize_config(self):
        if not self._parser:
            raise Exception("Optimize parser not load")
        return self._parser.optimize_config

    def load_config(self, path, stdio=None):
        self._optimize_config = None
        with FileUtil.open(path, 'rb') as f:
            config = self.loader.load(f)
            parser_version = config.get("optimize_version", None)
            parser = self._get_parser(version=parser_version)
            self._parser = parser
            self._load_default_optimizers(parser, stdio=stdio)
            self._optimize_config = parser.load(config)

    def _search_yaml_file(self, component, version, yaml_name, stdio=None):
        component_dir = os.path.join(self.path, component)
        if not os.path.exists(component_dir):
            stdio.verbose("no optimize config for component {}".format(component))
            return None
        yaml_file = os.path.join(component_dir, version, yaml_name)
        if not os.path.exists(yaml_file):
            stdio.verbose(
                'yaml file {} not found, try to get earlier version.'.format(yaml_file))
            final_version = Version('')
            versions = sorted([Version(v) for v in os.listdir(component_dir)], reverse=True)
            for v in versions:
                yaml_file = os.path.join(component_dir, v, yaml_name)
                if os.path.exists(yaml_file) and v <= version:
                    self.stdio.verbose('find earlier version yaml file: {}'.format(yaml_file))
                    break
            else:
                yaml_file = os.path.join(component_dir, final_version, yaml_name)
                stdio.verbose('try to use top yaml file: {}'.format(yaml_file))
                if not os.path.exists(yaml_file):
                    stdio.verbose('No such yaml file: {}'.format(yaml_file))
                    return None
        return yaml_file

    def load_default_config(self, test_name, stdio=None):
        self._optimize_config = None
        parser = self._get_parser()
        self._load_default_optimizers(parser, stdio=stdio)
        yaml_name = '{}.yaml'.format(test_name)
        for component, version in self.components.items():
            config_path = self._search_yaml_file(component, version, yaml_name, stdio=stdio)
            if config_path:
                with FileUtil.open(config_path, 'rb', stdio=stdio) as f:
                    config = self.loader.load(f)
                    parser.load_config_by_component(component, config, stdio=stdio)
        self._parser = parser

    def _load_default_optimizers(self, parser, stdio=None):
        yaml_name = 'optimizer.yaml'
        for component, version in self.components.items():
            optimizer_path = self._search_yaml_file(component, version, yaml_name, stdio=stdio)
            if optimizer_path:
                with FileUtil.open(optimizer_path, 'rb') as f:
                    config = self.loader.load(f)
                    parser.load_optimizer_by_component(component, config, stdio=stdio)

    @staticmethod
    def _get_latest_version(path):
        latest_version = Version('')
        for name in os.listdir(path):
            latest_version = max(latest_version, Version(name))
        return latest_version

    def _get_parser(self, version=None):
        if self._parser:
            return self._parser
        module_name = 'optimize_parser'
        class_name = 'OptimizeParser'
        file_name = '{}.py'.format(module_name)
        parser_base = os.path.join(self.path, module_name)
        if version is None:
            version = self._get_latest_version(parser_base)
        lib_path = os.path.join(parser_base, version)
        path = os.path.join(lib_path, file_name)
        if os.path.isfile(path):
            DynamicLoading.add_lib_path(lib_path)
            self.stdio.verbose('load optimize parser: {}'.format(path))
            module = DynamicLoading.import_module(module_name, self.stdio)
            try:
                self._parser = getattr(module, class_name)()
                return self._parser
            except:
                self.stdio.exception("")
                return None
            finally:
                DynamicLoading.remove_lib_path(lib_path)
        else:
            self.stdio.verbose('No such optimize parser: {}'.format(path))
            return None

    def register_component(self, name, version):
        self.stdio.verbose('register component {}-{} to optimize manager'.format(name, version))
        self.components[name] = Version(version)
