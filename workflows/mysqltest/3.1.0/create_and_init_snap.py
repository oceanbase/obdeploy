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
import const

def create_and_init_snap(plugin_context, workflow, repository, *args, **kwargs):
    env = plugin_context.namespace.get_variable("env")
    target_repository = repository
    snap_configs = kwargs.get('snap_configs')
    home_path = os.path.join(os.environ.get(const.CONST_OBD_HOME, os.getenv('HOME')), '.obd')
    fast_reboot = getattr(plugin_context.options, 'fast_reboot', False)
    use_snap = kwargs.get('use_snap')

    workflow.add_with_component_version(const.STAGE_FIRST, target_repository.name, target_repository.version, 'connect')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'mysqltest', target_repository.version, {"repository": target_repository}, 'init_pre')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'mysqltest', target_repository.version, {"repository": target_repository}, 'init')

    if fast_reboot and use_snap is False:
        for repository in plugin_context.repositories:
            if repository in snap_configs:
                workflow.add_with_component_version(const.STAGE_SECOND, repository.name, repository.version, 'stop')
                workflow.add_with_component_version_kwargs(const.STAGE_SECOND, 'general', "0.1", {"env": env, "snap_config": snap_configs[repository], "repository": target_repository}, 'create_snap')
                workflow.add_with_component_version_kwargs(const.STAGE_SECOND, repository.name, repository.version, {"home_path": home_path}, 'start')

        workflow.add_with_component_version(const.STAGE_THIRD, target_repository.name, target_repository.version, 'connect')
        workflow.add_with_component_version_kwargs(const.STAGE_THIRD, 'mysqltest', target_repository.version, {"repository": target_repository}, 'init')

    return plugin_context.return_true()
