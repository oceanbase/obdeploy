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


def standby_version_check(plugin_context, repository, primary_repositories, *args, **kwargs):
    stdio = plugin_context.stdio
    if not primary_repositories:
        stdio.error('Primary repositories not found.')
        return False
    for primary_repository in primary_repositories:
        if repository.name == primary_repository.name:
            if repository.version == primary_repository.version:
                return plugin_context.return_true()
            else:
                stdio.error('Version not match. standby version: {} , primary version: {}.'.format(repository.version, primary_repository.version))
                return False

    return plugin_context.return_false()

