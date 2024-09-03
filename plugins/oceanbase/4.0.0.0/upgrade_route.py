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

from _rpm import Version, Release, PackageInfo
from tool import YamlLoader, FileUtil


class VersionNode(PackageInfo):

    RELEASE_NULL = Release('0')

    def __init__(self, version, deprecated = False, require_from_binary = False):
        md5 = version
        version = version.split('_')
        release = version[1] if len(version) > 1 else self.RELEASE_NULL
        version = version[0]
        super(VersionNode, self).__init__('', version, release, '', md5, 0)
        self.next = []
        self.can_be_upgraded_to = []
        self.can_be_upgraded_to = []
        self.direct_come_from = []
        self.deprecated = deprecated
        self.require_from_binary = require_from_binary
        self.when_come_from = []
        self.when_upgraded_to = []
        self.direct_upgrade = False
        self.precursor = None

    def set_require_from_binary(self, require_from_binary):
        if isinstance(require_from_binary, dict):
            self.require_from_binary = require_from_binary.get('value')
            self.when_come_from = require_from_binary.get('when_come_from')
            self.when_upgraded_to = require_from_binary.get('when_upgraded_to')
            if None != self.when_come_from and None != self.when_upgraded_to:
                raise Exception("when_come_from and when_upgraded_to can not appear at the same time")
        else:
            self.require_from_binary = require_from_binary


class ObVersionGraph(object):

    def __init__(self, data):
        self.allNodes = {}
        self._build(data)

    def _build(self, data):
        for info in data:
            version = info.get('version')
            if version in self.allNodes:
                raise Exception("the version node '%s' was already exists, please check 'oceanbase_upgrade_dep.yml' to make sure there are no duplicate versions!" % version)
            node = VersionNode(version, info.get('deprecated', False))
            node.can_be_upgraded_to += info.get('can_be_upgraded_to', [])
            node.can_be_upgraded_to += info.get('can_be_upgraded_to', [])
            node.set_require_from_binary(info.get('require_from_binary', False))
            self.allNodes[version] = node
        for k in self.allNodes:
            v = self.allNodes[k]
            self.buildNeighbors(v, v.can_be_upgraded_to, False)
            self.buildNeighbors(v, v.can_be_upgraded_to, True)

    def buildNeighbors(self, current, neighborVersions, direct):
        for k in neighborVersions:
            node = self.allNodes.get(k)
            if node is None:
                node = VersionNode(k)
            if direct:
                node.direct_come_from.append(node)
            if node.release == VersionNode.RELEASE_NULL:
                current.next.append(node)
            else:
                current.next.insert(0, node)

    def get_node(self, repository):
        version = '%s-%s' % (repository.version , repository.release)
        if version in self.allNodes:
            return self.allNodes[version]
        
        find = None
        for k in self.allNodes:
            node = self.allNodes[k]
            if node.version == repository.version:
                if node > find:
                    find = node
        return find

    def findShortestUpgradePath(self, current_repository, dest_repository, stdio):
        start_node = self.get_node(current_repository)
        if not start_node:
            return
        queue = [start_node]
        visited = set([start_node])
        finalNode = None
        for k in self.allNodes:
            self.allNodes[k].precursor = None
    
        while queue:
            node = queue.pop(0)
            if node.version == dest_repository.version:
                if node.release == dest_repository.release:
                    finalNode = node
                    break
                if node.release == VersionNode.RELEASE_NULL:
                    flag = False
                    for v in node.next:
                        if v not in visited and v.version == dest_repository.version:
                            flag = True
                            v.precursor = node
                            queue.append(v)
                            visited.add(v)
                    if flag is False:
                        finalNode = node
            else:
                for v in node.next:
                    if v not in visited:
                        v.precursor = node
                        queue.append(v)
                        visited.add(v)
            if finalNode is not None:
                break
        
        p = finalNode
        pre = None
        res = []
        while p:
            res.insert(0, p)
            pre = p.precursor
            while pre and pre.precursor and p.version == pre.version:
                pre = pre.precursor
            p = pre
        
        n, i = len(res), 1
        while i < n:
            node = res[i]
            pre = res[i - 1]
            if pre in node.direct_come_from:
                node.direct_upgrade = True
            i += 1
        if len(res) == 1:
            res.insert(0, start_node)
        if len(res) > 0 and res[-1].deprecated:
            raise Exception('upgrade destination version:{}{} is deprecated, not support upgrade.'.format(res[-1].version, '-{}'.format(res[-1].release) if res[-1].release else ''))
        return format_route(res, current_repository)


def format_route(routes, repository):
    if not routes:
        return routes
    route_res = []
    from_version = repository.version
    from_release = repository.release
    for i, node in enumerate(routes):
        require_from_binary = getattr(node, 'require_from_binary', False)
        if getattr(node, 'when_come_from', False):
            require_from_binary = require_from_binary and (from_version in node.when_come_from or '%s-%s' % (from_version, from_release.split('.')[0]) in node.when_come_from)
            if require_from_binary:
                from_version = node.version
                from_release = node.release
        route_res.append({
                'version': node.version,
                'release': None if node.release == VersionNode.RELEASE_NULL else node.release,
                'direct_upgrade': getattr(node, 'direct_upgrade', False),
                'require_from_binary': require_from_binary
            })

    first_result = []
    second_result = [route_res[-1]]
    for j in range(len(route_res[1:-1]), 0, -1):
        if route_res[j].get('version') < '4.1.0.0':
            if route_res[j].get('require_from_binary'):
                first_result = route_res[1: j + 1]
                break
        elif route_res[j].get('require_from_binary'):
            second_result.insert(0, route_res[j])

    first_result.insert(0, route_res[0])
    return first_result + second_result



def upgrade_route(plugin_context, current_repository, dest_repository, *args, **kwargs):
    stdio = plugin_context.stdio
    repository_dir = dest_repository.repository_dir

    if dest_repository.version >= Version("4.4"):
        stdio.error('upgrade observer to version {} is not support, please upgrade obd first.'.format(dest_repository.version))
        return

    if current_repository.version == dest_repository.version:
        return plugin_context.return_true(route=format_route([current_repository, dest_repository], current_repository))

    upgrade_dep_name = 'etc/oceanbase_upgrade_dep.yml'
    upgrade_dep_path = os.path.join(repository_dir, upgrade_dep_name)
    if not os.path.isfile(upgrade_dep_path):
        stdio.error('%s No such file: %s. \n No upgrade route available' % (dest_repository, upgrade_dep_name))
        return

    version_dep = {}
    yaml = YamlLoader(stdio)

    try:
        with FileUtil.open(upgrade_dep_path, encoding='utf-8') as f:
            data = yaml.load(f)
            graph = ObVersionGraph(data)
            route = graph.findShortestUpgradePath(current_repository, dest_repository, plugin_context.stdio)
            if not route:
                raise Exception('No upgrade route available')
            plugin_context.return_true(route=route)
    except Exception as e:
        stdio.exception('fail to get upgrade graph: %s' % e)
