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

from _manager import Manager
from _rpm import PackageInfo
from _stdio import SafeStdio
from tool import YamlLoader, DirectoryUtil
from const import COMP_OBCLIENT, COMP_OCEANBASE_DIAGNOSTIC_TOOL, COMP_OBDIAG, TOOL_TPCH, TOOL_TPCC, TOOL_SYSBENCH, COMP_JRE


yaml = YamlLoader()

TOOLS = [COMP_OBCLIENT, COMP_OCEANBASE_DIAGNOSTIC_TOOL, TOOL_TPCH, TOOL_TPCC, TOOL_SYSBENCH, COMP_JRE]
TOOL_ALIAS = {
    COMP_OBDIAG: COMP_OCEANBASE_DIAGNOSTIC_TOOL,
}


class ToolConfig(SafeStdio, PackageInfo):
  
    def __init__(self, config_path, repo_manager, stdio=None):
        self.config_path = config_path
        self.name = os.path.basename(os.path.split(config_path)[0])
        self._data = None
        self.repo_manager = repo_manager
        self.stdio = stdio
    
    @property  
    def data(self):
        if self._data is None:
            # load .config from tool
            if not os.path.exists(self.config_path):
                self._data = {}
            else:
                with open(self.config_path, 'rb') as f:
                    self._data = yaml.load(f)
            # load .data from repository manager
            if self._data and self.repo_manager:
                repo = self.repo_manager.get_repository(self.name, self._data.get('version'), package_hash=self._data.get('hash'))
                self._data['arch'] = repo.arch
                self._data['size'] = repo.size
        return self._data
    
    @property
    def version(self):
        return self.data.get('version') if self.data else None
    
    @property
    def path(self):
        return self.data.get('path') if self.data else None
    
    @property
    def arch(self):
        return self.data.get('arch') if self.data else None
    
    @property
    def size(self):
        return self.data.get('size') if self.data else None
    
    @property
    def hash(self):
        return self.data.get('hash') if self.data else None
    
    def save(self, version, repo_hash, path):
        self.stdio.verbose('dump tool info to %s' % path)
        try:
            with open(self.config_path, 'w') as f:
                data = {
                    'version': version,
                    'hash': repo_hash,
                    'path': path
                }
                yaml.dump(data, f)
            return True
        except:
            self.stdio.exception('dump tool info to %s failed' % self.config_path)
        return False


class Tool(SafeStdio):
    CONFIG_YAML = '.config'
  
    def __init__(self, config_dir, repo_manager, stdio=None):
        self.config_path = os.path.join(config_dir, self.CONFIG_YAML)
        self.name = os.path.split(config_dir)[1]
        self._config = None
        self.stdio = stdio
        self.force = False
        self.repo_manager=repo_manager
        
    def set_force(self, force):
        self.force = force
        
    @property
    def config(self):
        return ToolConfig(self.config_path, self.repo_manager, self.stdio)
    
    def save_config(self, version, repo_hash, path):
        return self.config.save(version, repo_hash, path)
      
    def install(self, repository, install_path):
        if self.config.path == "" or self.config.path == "/" or self.config.path == os.getenv('HOME') or self.config.path == "/etc" or self.config.path == "/var":
            self.stdio.error('Refuse a high-risk deletion operation of tool %s' % self.name)
            return False
        elif self.config.path:
            if not self.uninstall():
                self.stdio.error('Failed to unintall the old version of tool %s' % self.name)
                return False
        else:
            pass
        if DirectoryUtil.copy(repository.repository_dir, install_path, self.stdio):
            return True
        else:
            return False
    
    def uninstall(self):
        if not self.config.path:
            self.stdio.error('Tool %s has no install folder' % self.name)
            return False
        if self.config.path == "" or self.config.path == "/" or self.config.path == os.getenv('HOME') or self.config.path == "/etc" or self.config.path == "/var":
            self.stdio.error('Refuse a high-risk deletion operation of tool %s' % self.name)
            return False
        if not DirectoryUtil.rm(self.config.path, self.stdio):
            self.stdio.error('remove tool %s failed' % self.name)
            return False
        return True


class ToolManager(Manager):

    RELATIVE_PATH = 'tool/'
    
    def __init__(self, home_path, repo_manager, lock_manager=None, stdio=None):
        super(ToolManager, self).__init__(home_path, stdio)
        self.lock_manager = lock_manager
        self.repo_manager = repo_manager
        
    def _lock(self, read_only=False):
        if self.lock_manager:
            if read_only:
                return self.lock_manager.mirror_and_repo_sh_lock()
            else:
                return self.lock_manager.mirror_and_repo_ex_lock()
        return True
        
    def get_tool_list(self):
        tools = []
        for name in os.listdir(self.path):
            path = os.path.join(self.path, name)
            if os.path.isdir(path):
                tools.append(Tool(path, self.repo_manager, stdio=self.stdio))
        return tools
      
    def is_belong_tool(self, name):
        name = TOOL_ALIAS.get(name, name)
        if name in TOOLS:
            return True
        return False
    
    def get_tool_offical_name(self, name):
        offical_name = None
        if not self.is_belong_tool(name):
            return offical_name
        name = TOOL_ALIAS.get(name, name)
        return name
    
    def get_support_tool_list(self):
        return TOOLS
    
    def get_tool_config_by_name(self, name):
        self._lock(True)
        path = os.path.join(self.path, name)
        if os.path.isdir(path):
            return Tool(path, self.repo_manager, stdio=self.stdio)
        return None
    
    def create_tool_config(self, name):
        self._lock()
        config_dir = os.path.join(self.path, name)
        self._mkdir(config_dir)
        return Tool(config_dir, self.repo_manager, stdio=self.stdio)
    
    def remove_tool_config(self, name):
        self._lock()
        config_dir = os.path.join(self.path, name)
        self._rm(config_dir)
        
    def install_tool(self, tool, repository, install_path):
        return tool.install(repository, install_path)
    
    def install_requirement(self, repository, install_path):
        if DirectoryUtil.copy(repository.repository_dir, install_path, self.stdio):
            return True
        else:
            return False
    
    def uninstall_tool(self, tool):
        return tool.uninstall()
    
    def update_tool(self, tool, repository, install_path):
        if not self.uninstall_tool(tool):
            return False
        if not self.install_tool(tool, repository, install_path):
            return False
        return True
    
    def is_tool_install(self, name):
        config_dir = os.path.join(self.path, name)
        if os.path.isdir(config_dir):
            return True
        return False
    
    def check_if_avaliable_update(self, tool, package):
        if package.version > tool.config.version:
            return True
        return False