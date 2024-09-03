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

from tool import ConfigUtil


class CommandVariables(dict):

    def __getitem__(self, item):
        if item not in self.items():
            return item
        else:
            return super(CommandVariables, self).__getitem__(item)


def load_variables_from_config(variables, component, config, command_variables, stdio=None):
    for variable in variables:
        if component not in ConfigUtil.get_list_from_dict(variable, 'components', str):
            continue
        variable_name = ConfigUtil.get_value_from_dict(variable, 'name', transform_func=str)
        config_key = ConfigUtil.get_value_from_dict(variable, 'config_key', transform_func=str)
        value = config.get(config_key)
        if value is not None:
            command_variables[variable_name] = str(value)
        if stdio:
            stdio.verbose('get variable %s for config key %s, value is %s' % (variable_name, config_key, value))


def prepare_variables(plugin_context, name, context, component, server, *args, **kwargs):
    def get_value_from_context(key, default=None):
        value = context.get(key, default)
        stdio.verbose('get value from context: %s value %s' % (key, value))
        return value

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_servers = cluster_config.servers

    components = get_value_from_context("components", [])
    servers = get_value_from_context("servers", [])
    cmd_conf = get_value_from_context("command_config")
    loading_env = {}

    if server is None:
        server = cluster_servers[0]
    if server not in cluster_servers and getattr(server, 'ip', server) in [s.ip for s in cluster_servers]:
        server = [s for s in cluster_servers if s.ip == getattr(server, 'ip', server)][0]
    # find command template
    command_template = None
    interactive = None
    wrapper_name = None
    no_exception = False
    no_interruption = False
    executor = None
    command_variables = CommandVariables()

    for command in cmd_conf.all_commands:
        cmd_name = ConfigUtil.get_value_from_dict(command, 'name', transform_func=str)
        allow_components = ConfigUtil.get_list_from_dict(command, 'components', str)
        if component in allow_components:
            current_command = ConfigUtil.get_value_from_dict(command, 'command', transform_func=str)
            loading_env[cmd_name] = current_command
            if name == cmd_name:
                command_template = current_command
                interactive = ConfigUtil.get_value_from_dict(command, 'interactive', transform_func=bool)
                wrapper_name = ConfigUtil.get_value_from_dict(command, 'wrapper', transform_func=str)
                no_exception = ConfigUtil.get_value_from_dict(command, 'no_exception', transform_func=bool)
                no_interruption = ConfigUtil.get_value_from_dict(command, 'no_interruption', transform_func=bool)
    if command_template is None:
        stdio.error(
            'There is no command {} in component {}. Please use --components to set the right component.'.format(name,
                                                                                                                 component))
        return

    if interactive and (len(components) > 1 or len(servers) > 1):
        stdio.error('Interactive commands do not support specifying multiple components or servers.')
        return
    cmd_input = None

    if server not in cluster_servers:
        if interactive:
            stdio.error("{} is not a server in {}".format(server, component))
            return plugin_context.return_false()
        else:
            stdio.verbose("{} is not a server in {}".format(server, component))
            return plugin_context.return_true(skip=True)

    global_config = cluster_config.get_global_conf()
    server_config = cluster_config.get_server_conf(server)
    client = clients[server]
    ssh_config = vars(client.config)

    # load global config
    stdio.verbose('load variables from global config')
    load_variables_from_config(cmd_conf.global_variables, component, global_config, command_variables, stdio)

    # load server config
    stdio.verbose('load variables from server config')
    load_variables_from_config(cmd_conf.server_variables, component, server_config, command_variables, stdio)

    # load ssh config
    stdio.verbose('load variables from ssh config')
    load_variables_from_config(cmd_conf.ssh_variables, component, ssh_config, command_variables, stdio)

    if wrapper_name:
        for wrapper in cmd_conf.all_wrappers:
            if wrapper_name == ConfigUtil.get_value_from_dict(wrapper, 'name', transform_func=str):
                local_command = ConfigUtil.get_value_from_dict(wrapper, "local_command", transform_func=str)
                remote_command = ConfigUtil.get_value_from_dict(wrapper, "remote_command", transform_func=str)
                command = ConfigUtil.get_value_from_dict(wrapper, "command", transform_func=str)
                cmd_input = ConfigUtil.get_value_from_dict(wrapper, "input", transform_func=str)
                executor = ConfigUtil.get_value_from_dict(wrapper, "executor", transform_func=str)
                if local_command and remote_command:
                    if client.is_localhost():
                        command = local_command
                    else:
                        command = remote_command
                command_template = command.format(cmd=command_template, **command_variables)
                if cmd_input:
                    cmd_input = cmd_input.format(cmd=command_template, **command_variables)
                break
        else:
            stdio.error("Wrapper {} not found in component {}.".format(wrapper_name, component))

    for key, value in loading_env.items():
        loading_env[key] = str(value).format(**command_variables)

    context.update(
        command_variables=command_variables, command_config=cmd_conf, command_template=command_template,
        interactive=interactive, cmd_input=cmd_input, no_exception=no_exception, no_interruption=no_interruption,
        component=component, server=server, env=loading_env, executor=executor)
    return plugin_context.return_true()
