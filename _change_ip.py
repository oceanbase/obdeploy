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

import os
import shutil
import stat
import tempfile
from copy import deepcopy
from datetime import datetime

from ruamel.yaml.comments import CommentedMap

import const
from _deploy import ConfigParser, ObserverIdentity, ObserverIdentityError, ServerConfig
from tool import Cursor, YamlLoader


class ChangeIpError(Exception):
    pass


class ChangeIpPlan(object):

    def __init__(self, data, changed_components, changed_servers):
        self.data = data
        self.changed_components = changed_components
        self.changed_servers = changed_servers

    @property
    def replacement_count(self):
        return len(self.changed_servers)


class DeploymentAddressChanger(object):
    """Build and atomically commit a deployment management-IP replacement."""

    @staticmethod
    def _call_stdio(stdio, func, message):
        callback = getattr(stdio, func, None) if stdio else None
        return callback(message) if callback else None

    @staticmethod
    def validate_ip(ip):
        try:
            ConfigParser._get_server(ip)
        except Exception:
            raise ChangeIpError('Invalid IP address: %s' % ip)
        return ip

    @staticmethod
    def _server_lists(component_name, component_config):
        style = component_config.get('style', 'default')
        if style == 'cluster':
            zones = component_config.get('zones')
            if not isinstance(zones, dict):
                raise ChangeIpError('Component %s has an invalid cluster-style zones configuration' % component_name)
            server_lists = []
            for zone_name, zone_config in zones.items():
                if not isinstance(zone_config, dict) or not isinstance(zone_config.get('servers', []), list):
                    raise ChangeIpError(
                        'Component %s zone %s has an invalid servers configuration' % (component_name, zone_name))
                server_lists.append(zone_config.get('servers', []))
            return server_lists

        servers = component_config.get('servers', [])
        if not isinstance(servers, list):
            raise ChangeIpError('Component %s has an invalid servers configuration' % component_name)
        return [servers]

    @staticmethod
    def _server_value(server):
        if isinstance(server, dict):
            if 'ip' not in server:
                raise ChangeIpError('Server object is missing the ip field')
            return str(server['ip']), str(server.get('name') or server['ip'])
        return str(server), str(server)

    @classmethod
    def build_plan(cls, source_data, component_names, old_ip, new_ip):
        cls.validate_ip(old_ip)
        cls.validate_ip(new_ip)
        if old_ip == new_ip:
            raise ChangeIpError('The old and new IP addresses are identical')

        candidate_data = deepcopy(source_data)
        entries = []
        for component_name in component_names:
            component_config = candidate_data.get(component_name)
            if not isinstance(component_config, dict):
                raise ChangeIpError('Component %s configuration is missing' % component_name)
            for servers in cls._server_lists(component_name, component_config):
                for index, server in enumerate(servers):
                    ip, name = cls._server_value(server)
                    entries.append((component_name, servers, index, server, ip, name))

        conflicts = sorted(set(
            '%s/%s' % (component_name, name)
            for component_name, _, _, _, ip, name in entries
            if ip == new_ip
        ))
        if conflicts:
            raise ChangeIpError(
                'The new IP %s is already used by: %s' % (new_ip, ', '.join(conflicts)))

        changed_components = []
        changed_servers = []
        for component_name, servers, index, server, ip, name in entries:
            if ip != old_ip:
                continue
            if isinstance(server, dict):
                if not server.get('name'):
                    server['name'] = name
                server['ip'] = new_ip
            else:
                replacement = CommentedMap()
                replacement['name'] = name
                replacement['ip'] = new_ip
                servers[index] = replacement
            if component_name not in changed_components:
                changed_components.append(component_name)
            changed_servers.append((component_name, name))

        if not changed_servers:
            raise ChangeIpError('The old IP %s was not found in this deployment' % old_ip)
        return ChangeIpPlan(candidate_data, changed_components, changed_servers)

    @classmethod
    def verify_ssh(cls, user_config, new_ip, ssh_connect, stdio=None):
        target = ServerConfig(new_ip, 'change-ip-target')
        clients = {}
        try:
            ssh_connect([target], clients, user_config, fail_exit=False)
            if target not in clients:
                cls._call_stdio(
                    stdio,
                    'error',
                    'Cannot connect to the new management IP %s with the deployment SSH credentials.' % new_ip
                )
                return False
            return True
        finally:
            for client in clients.values():
                client.close(stdio=stdio)

    @classmethod
    def verify_database(cls, candidate_config, new_ip, stdio=None):
        standalone_config = candidate_config.components[const.COMP_OB_STANDALONE]
        server = standalone_config.servers[0]
        server_config = standalone_config.get_server_conf(server)
        cursor = None
        cls._call_stdio(stdio, 'start_loading', 'Verify observer identity through the new management IP')
        try:
            cursor = Cursor(
                ip=new_ip,
                port=server_config.get('mysql_port', 2881),
                tenant='',
                password=server_config.get('root_password', '') or '',
                stdio=stdio
            )
            raw_servers = cursor.fetchall(
                'select svr_ip, svr_port, inner_port from oceanbase.__all_server',
                raise_exception=True,
                stdio=stdio
            )
            ObserverIdentity.verify(standalone_config, raw_servers)
            cls._call_stdio(stdio, 'stop_loading', 'succeed')
            return True
        except Exception as error:
            cls._call_stdio(stdio, 'stop_loading', 'fail')
            cls._call_stdio(
                stdio,
                'error',
                'Failed to verify the running standalone observer through %s: %s' % (new_ip, error)
            )
            return False
        finally:
            if cursor:
                cursor.close()

    @staticmethod
    def validate_candidate(original_config, candidate_config, old_ip, new_ip):
        if list(original_config.components.keys()) != list(candidate_config.components.keys()):
            raise ChangeIpError('The candidate configuration changed the deployment component list')
        for component_name in original_config.components:
            old_servers = original_config.components[component_name].servers
            new_servers = candidate_config.components[component_name].servers
            expected = [
                (server.name, new_ip if server.ip == old_ip else server.ip)
                for server in old_servers
            ]
            actual = [(server.name, server.ip) for server in new_servers]
            if expected != actual:
                raise ChangeIpError(
                    'The candidate configuration changed unexpected servers for component %s' % component_name)

        standalone_config = candidate_config.components.get(const.COMP_OB_STANDALONE)
        try:
            marker = ObserverIdentity.marker(standalone_config)
        except ObserverIdentityError as error:
            raise ChangeIpError(str(error))
        if not marker or marker['state'] != const.OBSERVER_IDENTITY_VERIFIED:
            raise ChangeIpError('The standalone loopback observer identity is not verified')

    @staticmethod
    def stage(config_path, data, stdio=None):
        yaml_loader = YamlLoader(stdio=stdio)
        config_dir = os.path.dirname(config_path)
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(
                prefix='.%s.change-ip.' % os.path.basename(config_path),
                suffix='.tmp',
                dir=config_dir
            )
            with os.fdopen(fd, 'w') as f:
                yaml_loader.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(temp_path, stat.S_IMODE(os.stat(config_path).st_mode))
            return temp_path
        except Exception as error:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            raise ChangeIpError('Failed to stage the new deployment configuration: %s' % error)

    @staticmethod
    def _fsync_directory(path):
        directory_fd = None
        try:
            directory_fd = os.open(path, os.O_RDONLY)
            os.fsync(directory_fd)
        finally:
            if directory_fd is not None:
                os.close(directory_fd)

    @classmethod
    def commit(cls, config_path, candidate_path):
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        backup_path = '%s.change-ip.%s.bak' % (config_path, timestamp)
        config_dir = os.path.dirname(config_path)
        replaced = False
        try:
            shutil.copy2(config_path, backup_path)
            with open(backup_path, 'rb') as backup_file:
                os.fsync(backup_file.fileno())
            os.rename(candidate_path, config_path)
            replaced = True
            cls._fsync_directory(config_dir)
            return backup_path
        except Exception as error:
            if os.path.exists(candidate_path):
                os.remove(candidate_path)
            if replaced:
                try:
                    cls.restore(config_path, backup_path)
                except Exception as restore_error:
                    raise ChangeIpError(
                        'Failed to commit the deployment configuration and automatic restore failed: %s. '
                        'Restore manually from %s. Restore error: %s' %
                        (error, backup_path, restore_error)
                    )
            raise ChangeIpError('Failed to commit the deployment configuration: %s' % error)

    @classmethod
    def restore(cls, config_path, backup_path):
        config_dir = os.path.dirname(config_path)
        restore_path = None
        try:
            fd, restore_path = tempfile.mkstemp(
                prefix='.%s.change-ip-restore.' % os.path.basename(config_path),
                suffix='.tmp',
                dir=config_dir
            )
            os.close(fd)
            shutil.copy2(backup_path, restore_path)
            os.rename(restore_path, config_path)
            restore_path = None
            cls._fsync_directory(config_dir)
            return True
        except Exception as error:
            raise ChangeIpError('Failed to restore %s from %s: %s' % (config_path, backup_path, error))
        finally:
            if restore_path and os.path.exists(restore_path):
                os.remove(restore_path)
