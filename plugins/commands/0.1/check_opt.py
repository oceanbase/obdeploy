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

from tool import YamlLoader, ConfigUtil

ALLOWED_LEVEL = [0, 1, 2]
YAML_LOADER = YamlLoader()
YAML_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "command_template.yaml")


class CommandConfig(object):

    def __init__(self, yaml_path=YAML_TEMPLATE_PATH, loader=YAML_LOADER, stdio=None):
        self.yaml_path = yaml_path
        self.loader = loader
        self.stdio = stdio
        self._load()

    def _load(self):
        try:
            with open(self.yaml_path, 'rb') as f:
                self._data = self.loader.load(f)
                self.all_variables = self._data.get('variables')
                self.global_variables = self.all_variables.get('global', [])
                self.server_variables = self.all_variables.get('server', [])
                self.ssh_variables = self.all_variables.get('ssh', [])
                self.all_commands = self._data.get('commands', [])
                self.all_wrappers = self._data.get('wrappers', [])
        except:
            if self.stdio:
                self.stdio.exception('failed to load command template')


def check_opt(plugin_context, name, context, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
            stdio.verbose('get option: %s value %s' % (key, value))
        return value

    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    clients = plugin_context.clients
    deployed_components = list(plugin_context.components)

    components = get_option("components", None)
    servers = get_option("servers", None)

    interactive = False
    command_config = CommandConfig()
    for command in command_config.all_commands:
        command_name = ConfigUtil.get_value_from_dict(command, 'name', transform_func=str)
        if command_name == name:
            interactive = ConfigUtil.get_value_from_dict(command, 'interactive', False, transform_func=bool)

    if components is None:
        if interactive:
            components = deployed_components[:1]
            stdio.verbose("Component {} will be used according to the order in the deploy configuration yaml.".format(components[0]))
        else:
            components = deployed_components
            stdio.verbose("Component {} will be used because {} is a non-interactive command".format(", ".join(components), name))
    elif components == "*":
        components = deployed_components
    else:
        components = components.split(',')

    if not clients:
        stdio.error("{} server list is empty".format(','.join(components)))
        return
    if servers is None:
        if interactive:
            servers = cluster_config.servers[:1]
            stdio.verbose("Server {} will be used according to the order in the deploy configuration yaml.".format(servers[0]))
        else:
            servers = list(clients.keys())
            stdio.verbose("Server {} will be used because {} is a non-interactive command".format(", ".join([str(s) for s in servers]), name))
    elif servers == '*':
        servers = list(clients.keys())
    else:
        server_names = servers.split(',')
        servers = set()
        for server in clients:
            if server.ip in server_names:
                server_names.remove(server.ip)
                servers.add(server)
            if server.name in server_names:
                server_names.remove(server.name)
                servers.add(server)
        if server_names:
            stdio.error("Server {} not found in current deployment".format(','.join(server_names)))
            return

    failed_components = []
    for component in components:
        if component not in deployed_components:
            failed_components.append(component)
    if failed_components:
        stdio.error('{} not support. {} is allowed'.format(','.join(failed_components), deployed_components))
        return plugin_context.return_false()
    context.update(components=components, servers=list(servers), command_config=command_config)
    return plugin_context.return_true(context=context)
