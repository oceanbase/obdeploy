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
import base64
from copy import deepcopy
from optparse import Values

from Crypto import Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_signature
from Crypto.Cipher import PKCS1_OAEP as PKCS1_cipher

import const

PRI_KEY_FILE = '.ocp-express'
PUB_KEY_FILE = '.ocp-express.pub'


def generate_key(client, key_dir, stdio):
    rsa = RSA.generate(1024)
    private_key = rsa
    public_key = rsa.publickey()
    client.write_file(private_key.exportKey(pkcs=8), os.path.join(key_dir, PRI_KEY_FILE), mode='wb', stdio=stdio)
    client.write_file(public_key.exportKey(pkcs=8), os.path.join(key_dir, PUB_KEY_FILE), mode='wb', stdio=stdio)
    return private_key, public_key


def get_key(client, key_dir, stdio):
    private_key_file = os.path.join(key_dir, PRI_KEY_FILE)
    ret = client.execute_command("cat {}".format(private_key_file))
    if not ret:
        return generate_key(client, key_dir, stdio)
    private_key = RSA.importKey(ret.stdout.strip())
    public_key_file = os.path.join(key_dir, PUB_KEY_FILE)
    ret = client.execute_command("cat {}".format(public_key_file))
    if not ret:
        return generate_key(client, key_dir, stdio)
    public_key = RSA.importKey(ret.stdout.strip())
    return private_key, public_key


def get_plain_public_key(public_key):
    if isinstance(public_key, RSA.RsaKey):
        public_key = public_key.exportKey(pkcs=8).decode()
    elif isinstance(public_key, bytes):
        public_key = public_key.decode()
    public_key = public_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "").replace("\n", "")
    return public_key


def rsa_private_sign(passwd, private_key):
    signer = PKCS1_cipher.new(private_key)
    sign = signer.encrypt(passwd.encode("utf-8"))
    # digest = SHA.new()
    # digest.update(passwd.encode("utf8"))
    # sign = signer.sign(digest)
    signature = base64.b64encode(sign)
    signature = signature.decode('utf-8')
    return signature


def get_missing_required_parameters(parameters):
    results = []
    for key in ["jdbc_url", "jdbc_password", "jdbc_username", "cluster_name", "ob_cluster_id", "root_sys_password",
                "server_addresses", "agent_username", "agent_password"]:
        if parameters.get(key) is None:
            results.append(key)
    return results


def prepare_parameters(cluster_config, stdio):
    # depends config
    env = {}
    depend_observer = False
    depend_info = {}
    ob_servers_conf = {}
    root_servers = []
    for comp in const.COMPS_OB:
        ob_zones = {}
        if comp in cluster_config.depends:
            depend_observer = True
            observer_globals = cluster_config.get_depend_config(comp)
            ocp_meta_keys = [
                "ocp_meta_tenant", "ocp_meta_db", "ocp_meta_username", "ocp_meta_password", "appname", "cluster_id", "root_password"
            ]
            for key in ocp_meta_keys:
                value = observer_globals.get(key)
                if value is not None:
                    depend_info[key] = value
            ob_servers = cluster_config.get_depend_servers(comp)
            connect_infos = []
            for ob_server in ob_servers:
                ob_servers_conf[ob_server] = ob_server_conf = cluster_config.get_depend_config(comp, ob_server)
                connect_infos.append([ob_server.ip, ob_server_conf['mysql_port']])
                zone = ob_server_conf['zone']
                if zone not in ob_zones:
                    ob_zones[zone] = ob_server
            depend_info['connect_infos'] = connect_infos
            root_servers = ob_zones.values()
            break
    for comp in const.COMPS_ODP:
        if comp in cluster_config.depends:
            obproxy_servers = cluster_config.get_depend_servers(comp)
            obproxy_server = obproxy_servers[0]
            obproxy_server_config = cluster_config.get_depend_config(comp, obproxy_server)
            depend_info['server_ip'] = obproxy_server.ip
            depend_info['mysql_port'] = obproxy_server_config['listen_port']
            break
    if const.COMP_OBAGENT in cluster_config.depends:
        obagent_servers = cluster_config.get_depend_servers('obagent')
        server_addresses = []
        for obagent_server in obagent_servers:
            obagent_server_config_without_default = cluster_config.get_depend_config('obagent', obagent_server, with_default=False)
            obagent_server_config = cluster_config.get_depend_config('obagent', obagent_server)
            username = obagent_server_config['http_basic_auth_user']
            password = obagent_server_config['http_basic_auth_password']
            if 'obagent_username' not in depend_info:
                depend_info['obagent_username'] = username
            elif depend_info['obagent_username'] != username:
                stdio.error('The http basic auth of obagent is inconsistent')
                return
            if 'obagent_password' not in depend_info:
                depend_info['obagent_password'] = password
            elif depend_info['obagent_password'] != password:
                stdio.error('The http basic auth of obagent is inconsistent')
                return
            if obagent_server_config_without_default.get('sql_port'):
                sql_port = obagent_server_config['sql_port']
            elif ob_servers_conf.get(obagent_server) and ob_servers_conf[obagent_server].get('mysql_port'):
                sql_port = ob_servers_conf[obagent_server]['mysql_port']
            else:
                continue
            if obagent_server_config_without_default.get('rpc_port'):
                svr_port = obagent_server_config['rpc_port']
            elif ob_servers_conf.get(obagent_server) and ob_servers_conf[obagent_server].get('rpc_port'):
                svr_port = ob_servers_conf[obagent_server]['rpc_port']
            else:
                continue
            server_addresses.append({
                "address": obagent_server.ip,
                "svrPort": svr_port,
                "sqlPort": sql_port,
                "withRootServer": obagent_server in root_servers,
                "agentMgrPort": obagent_server_config.get('mgragent_http_port', 0),
                "agentMonPort": obagent_server_config.get('monagent_http_port', 0)
            })
        depend_info['server_addresses'] = server_addresses

    for server in cluster_config.servers:
        server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        original_server_config = cluster_config.get_original_server_conf(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                if depend_info.get('server_ip'):
                    server_config['ocp_meta_db'] = depend_info.get('ocp_meta_db')
                    server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'], depend_info['mysql_port'], depend_info['ocp_meta_db'])
                else:
                    server_config['connect_infos'] = depend_info.get('connect_infos')
                    server_config['ocp_meta_db'] = depend_info.get('ocp_meta_db')
                    server_config['jdbc_url'] = ''
            if 'jdbc_username' in missed_keys and depend_observer:
                server_config['jdbc_username'] = "{}@{}".format(depend_info['ocp_meta_username'], depend_info.get('ocp_meta_tenant', {}).get("tenant_name"))
            depends_key_maps = {
                "jdbc_password": "ocp_meta_password",
                "cluster_name": "appname",
                "ob_cluster_id": "cluster_id",
                "root_sys_password": "root_password",
                "agent_username": "obagent_username",
                "agent_password": "obagent_password",
                "server_addresses": "server_addresses"
            }
            for key in depends_key_maps:
                if key in missed_keys:
                    if depend_info.get(depends_key_maps[key]) is not None:
                        server_config[key] = depend_info[depends_key_maps[key]]
        env[server] = server_config
    return env


def parameter_pre(plugin_context, **kwargs):
    check_status = plugin_context.get_variable('start_check_status')
    check_pass = plugin_context.get_variable('check_pass')
    check_fail = plugin_context.get_variable('check_fail')
    critical = plugin_context.get_variable('critical')
    get_option = plugin_context.get_variable('get_option')
    error = plugin_context.get_variable('error')

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    env = prepare_parameters(cluster_config, stdio)
    if not env:
        return plugin_context.return_false()

    ocp_tenants = []
    tenants_componets_map = {
        "meta": ["ocp-express", "ocp-server", "ocp-server-ce"],
        "monitor": ["ocp-server", "ocp-server-ce"],
    }
    ocp_tenant_keys = ['tenant', 'db', 'username', 'password']
    server_config = env[cluster_config.servers[0]]
    removed_components = cluster_config.get_deploy_removed_components()
    if kwargs.get('workflow_name', 'start') != 'destroy':
        for tenant in tenants_componets_map:
            prefix = "ocp_%s_" % tenant

            # set create tenant variable
            for key in server_config:
                if key.startswith(prefix) and server_config.get(key, None):
                    server_config[prefix + 'tenant'][key.replace(prefix, '', 1)] = server_config[key]
            tenant_info = server_config[prefix + "tenant"]
            tenant_info["variables"] = "ob_tcp_invited_nodes='%'"
            tenant_info["create_if_not_exists"] = True
            tenant_info["database"] = server_config.get(prefix + "db")
            tenant_info["db_username"] = server_config.get(prefix + "username")
            tenant_info["db_password"] = server_config.get(prefix + "password", "")
            tenant_info["{0}_root_password".format(tenant_info['tenant_name'])] = server_config.get(prefix + "password", "")
            ocp_tenants.append(Values(tenant_info))


    clean_data = (not cluster_config.depends or len(removed_components) > 0 and len(removed_components.intersection({const.COMP_OB, const.COMP_OB_CE})) == 0) and stdio.confirm("Would you like to clean meta data ？")
    plugin_context.set_variable("clean_data", clean_data)
    plugin_context.set_variable("create_tenant_options", ocp_tenants)
    plugin_context.set_variable('get_key', get_key)
    plugin_context.set_variable('get_plain_public_key', get_plain_public_key)
    plugin_context.set_variable('rsa_private_sign', rsa_private_sign)
    plugin_context.set_variable('get_missing_required_parameters', get_missing_required_parameters)
    plugin_context.set_variable('start_env', env)
    return plugin_context.return_true(create_tenant_options=ocp_tenants)
