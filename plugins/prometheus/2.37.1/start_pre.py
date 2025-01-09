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

import os
import re
import bcrypt

from tool import YamlLoader, FileUtil
from _rpm import Version
from copy import deepcopy

def hashed_with_bcrypt(content):
    content_bytes = content.encode('utf-8')
    hash_str = bcrypt.hashpw(content_bytes, bcrypt.gensalt())
    return hash_str.decode()


def load_config_from_obagent(cluster_config, obagent_repo, stdio, client, server, server_config, yaml):
    stdio.verbose('load config from obagent')
    server_home_path = server_config['home_path']
    port = server_config['port']
    address = server_config['address']
    obagent_servers = cluster_config.get_depend_servers('obagent')
    prometheus_conf_dir = os.path.join(obagent_repo.repository_dir, 'conf/prometheus_config')
    prometheus_conf_path = os.path.join(prometheus_conf_dir, 'prometheus.yaml')
    rules_dir = os.path.join(prometheus_conf_dir, 'rules')
    remote_rules_dir = os.path.join(server_home_path, 'rules')

    obagent_targets = []
    http_basic_auth_user = None
    http_basic_auth_password = None
    watershed = Version('1.3.0')
    for obagent_server in obagent_servers:
        obagent_server_config = cluster_config.get_depend_config('obagent', obagent_server)
        if obagent_repo.version < watershed:
            server_port = obagent_server_config['server_port']
        else:
            server_port = obagent_server_config['monagent_http_port']
        obagent_targets.append('{}:{}'.format(obagent_server.ip, server_port))
        if http_basic_auth_user is None:
            http_basic_auth_user = obagent_server_config['http_basic_auth_user']
        if http_basic_auth_password is None:
            http_basic_auth_password = obagent_server_config['http_basic_auth_password']
    if not os.path.exists(prometheus_conf_path):
        raise Exception('prometheus config template do not exists.')
    try:
        with FileUtil.open(prometheus_conf_path, stdio=stdio) as f:
            content = f.read()
        split = re.search(r'(\s+\-\s+)\{target\}', content).group(1)
        targets = split.join(obagent_targets)
        content = content.format(
            http_basic_auth_user=http_basic_auth_user,
            http_basic_auth_password=http_basic_auth_password,
            target=targets
        )
        if not client.put_dir(rules_dir, remote_rules_dir):
            raise Exception('failed to put {} to {} {}'.format(rules_dir, client, remote_rules_dir))
        prometheus_conf_from_obagent = yaml.loads(content)
        scrape_configs = []
        if 'scrape_configs' in prometheus_conf_from_obagent and prometheus_conf_from_obagent['scrape_configs']:
            for scrape_config in prometheus_conf_from_obagent['scrape_configs']:
                if scrape_config.get('job_name') == 'prometheus':
                    if "basic_auth_users" in server_config and server_config["basic_auth_users"]:
                        for username, password in server_config["basic_auth_users"].items():
                            scrape_config['basic_auth'] = {"username": username, "password": password}
                            break
                    if address == '0.0.0.0':
                        prometheus_address = "{}:{}".format(server.ip, port)
                    else:
                        prometheus_address = "{}:{}".format(address, port)
                    scrape_config["static_configs"] = [{"targets": [prometheus_address]}]
                else:
                    scrape_config['file_sd_configs'] = [{"files": ["targets/*.yaml"]}]
                scrape_configs.append(scrape_config)
        prometheus_conf_from_obagent['scrape_configs'] = scrape_configs
        return prometheus_conf_from_obagent
    except Exception as e:
        stdio.exception('failed to load prometheus conf from obagent')
        raise e


def start_pre(plugin_context, *args, **kwargs):
    def generate_or_update_config():
        prometheus_conf_content = None
        if client.execute_command('ls {}'.format(runtime_prometheus_conf)):
            try:
                ret = client.execute_command('cat {}'.format(runtime_prometheus_conf))
                if not ret:
                    raise Exception(ret.stderr)
                prometheus_conf_content = yaml.loads(ret.stdout.strip())
            except:
                stdio.exception('')
                stdio.warn('{}: invalid prometheus config {}, regenerate a new config.'.format(server, runtime_prometheus_conf))
        if prometheus_conf_content is None:
            if obagent_repo:
                try:
                    prometheus_conf_content = load_config_from_obagent(cluster_config, obagent_repo, stdio, client, server, server_config, yaml=yaml)
                except Exception as e:
                    stdio.exception(e)
                    return False
            else:
                prometheus_conf_content = {'global': None}
        if not without_parameter and config:
            prometheus_conf_content.update(config)
        try:
            config_content = yaml.dumps(prometheus_conf_content).strip()
            if not client.write_file(config_content, runtime_prometheus_conf):
                stdio.error('failed to write config file {}'.format(runtime_prometheus_conf))
                return False
            return True
        except Exception as e:
            stdio.exception(e)
            return False

    def check_parameter(key):
        if key in invalid_key_map:
            stdio.warn('{} invalid additional parameter {}, please set configuration {} instead.'.format(server, key, invalid_key_map[key]))
            return False
        return True

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    options = plugin_context.options
    prometheusd_path = os.path.join(os.path.split(__file__)[0], 'prometheusd.sh')
    without_parameter = getattr(options, 'without_parameter', False)
    invalid_key_map = {
        'web.listen-address': 'port & address',
        'web.enable-lifecycle': 'enable_lifecycle',
        'web.config.file': 'web_config & basic_auth_users',
        'storage.tsdb.path': 'data_dir',
    }
    yaml = YamlLoader(stdio=stdio)
    pid_path = {}
    cmd_args_map = {}
    obagent_repo = None
    if 'obagent' in cluster_config.depends:
        for repository in plugin_context.repositories:
            if repository.name == 'obagent':
                stdio.verbose('obagent version: {}'.format(repository.version))
                obagent_repo = repository
                break

    if not os.path.exists(prometheusd_path):
        stdio.error('{} not exist'.format(prometheusd_path))
        stdio.stop_loading('fail')
        return False

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        pid_path[server] = os.path.join(home_path, 'run/prometheus.pid')
        runtime_prometheus_conf = os.path.join(home_path, 'prometheus.yaml')
        config = server_config.get('config', {})
        port = server_config['port']
        address = server_config['address']
        flag_file = os.path.join(home_path, '.prometheus_started')
        if not client.execute_command('ls {}'.format(flag_file)):
            without_parameter = False
        if not generate_or_update_config():
            stdio.stop_loading('fail')
            return False
        cmd_items = ['--config.file={}'.format(runtime_prometheus_conf)]
        cmd_items.append('--web.listen-address={}:{}'.format(address, port))
        cmd_items.append('--storage.tsdb.path={}'.format(os.path.join(home_path, 'data')))
        enable_lifecycle = server_config['enable_lifecycle']
        if enable_lifecycle:
            cmd_items.append('--web.enable-lifecycle')
        basic_auth_users = deepcopy(server_config.get('basic_auth_users', {}))
        web_config = deepcopy(server_config.get('web_config', {}))
        if basic_auth_users or web_config:
            if 'basic_auth_users' in web_config:
                stdio.warn('{}: basic_auth_users do not work in web_config, please set basic_auth_users in configuration.'.format(server))
                return False
            try:
                for k, v in basic_auth_users.items():
                    basic_auth_users[str(k)] = hashed_with_bcrypt(str(v))
                web_config['basic_auth_users'] = basic_auth_users
                web_config_path = os.path.join(home_path, 'web_config.yaml')
                if not client.write_file(yaml.dumps(web_config), web_config_path):
                    stdio.error('{}: failed to write web config {}'.format(server, web_config_path))
                    return False
            except Exception as e:
                stdio.exception(e)
                return False
            cmd_items.append('--web.config.file={}'.format(web_config_path))
        additional_parameters = server_config.get('additional_parameters')
        if additional_parameters:
            check_ret = True
            for parameter in additional_parameters:
                if isinstance(parameter, dict):
                    for k, v in parameter.items():
                        if not check_parameter(k):
                            check_ret = False
                        cmd_items.append('--{}={}'.format(k, v))
                else:
                    if parameter in invalid_key_map:
                        if not check_parameter(parameter):
                            check_ret = False
                    cmd_items.append('--{}'.format(parameter))
            if not check_ret:
                stdio.stop_loading('fail')
                return False
        cmd_args_map[server] = cmd_items

    plugin_context.set_variable('cmd_args_map', cmd_args_map)
    return plugin_context.return_true()