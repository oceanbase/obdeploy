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

from _rpm import Version


def upgrade_check(plugin_context, upgrade_repositories, *args, **kwargs):
    stdio = plugin_context.stdio
    dest_repository = upgrade_repositories[1]
    if dest_repository.version >= Version('4.2.1'):
        for repository in plugin_context.repositories:
            if repository.name == 'obagent' and repository.version < Version('4.2.1'):
                stdio.error('OCP express {} requires obagent with version 4.2.1 or above, current obagent version is {}'.format(dest_repository.version, repository.version))
                return False

    plugin_context.return_true()
