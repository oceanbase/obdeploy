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

import hashlib


def start_pre(plugin_context, need_bootstrap=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    options = plugin_context.options
    clusters_cmd = {}
    real_cmd = {}
    pid_path = {}
    obproxy_config_server_url = plugin_context.get_variable('obproxy_config_server_url')

    if getattr(options, 'without_parameter', False):
        use_parameter = False
    else:
        # Bootstrap is required when starting with parameter, ensure the passwords are correct.
        need_bootstrap = True
        use_parameter = True

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        if not server_config.get('obproxy_config_server_url') and obproxy_config_server_url:
            server_config['obproxy_config_server_url'] = obproxy_config_server_url

        if not client.execute_command('ls %s/etc/obproxy_config.bin' % home_path):
            need_bootstrap = True

        pid_path[server] = "%s/run/obproxy-%s-%s.pid" % (home_path, server.ip, server_config["listen_port"])

        if use_parameter:
            not_opt_str = [
                'listen_port',
                'prometheus_listen_port',
                'rs_list',
                'cluster_name'
            ]
            start_unuse = ['home_path', 'observer_sys_password', 'obproxy_sys_password', 'observer_root_password']
            get_value = lambda key: "'%s'" % server_config[key] if isinstance(server_config[key], str) else server_config[key]
            opt_str = []
            if server_config.get('obproxy_sys_password'):
                obproxy_sys_password = hashlib.sha1(server_config['obproxy_sys_password'].encode("utf-8")).hexdigest()
            else:
                obproxy_sys_password = ''
            opt_str.append("obproxy_sys_password='%s'" % obproxy_sys_password)
            for key in server_config:
                if key not in start_unuse and key not in not_opt_str:
                    value = get_value(key)
                    opt_str.append('%s=%s' % (key, value))
            cmd = ['-o %s' % ','.join(opt_str)]
            for key in not_opt_str:
                if key in server_config:
                    value = get_value(key)
                    cmd.append('--%s %s' % (key, value))
        else:
            cmd = ['--listen_port %s' % server_config.get('listen_port')]

        real_cmd[server] = '%s/bin/obproxy %s' % (home_path, ' '.join(cmd))
        clusters_cmd[server] = 'cd %s; %s' % (home_path, real_cmd[server])
    plugin_context.set_variable('clusters_cmd', clusters_cmd)
    plugin_context.set_variable('real_cmd', real_cmd)
    plugin_context.set_variable('need_bootstrap', need_bootstrap)
    plugin_context.set_variable('pid_path', pid_path)
    plugin_context.return_true()

