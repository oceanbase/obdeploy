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

import json
import os
import re
import time
import base64
import sys
from copy import deepcopy

from _types import Capacity, CapacityWithB
from tool import FileUtil, YamlLoader, ConfigUtil, Cursor

from Crypto import Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_signature
from Crypto.Cipher import PKCS1_OAEP as PKCS1_cipher

from _errno import EC_SQL_EXECUTE_FAILED


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


def get_port_socket_inode(client, port, stdio):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def confirm_port(client, pid, port, stdio):
    socket_inodes = get_port_socket_inode(client, port, stdio)
    if not socket_inodes:
        return False
    ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False


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
    for comp in ["oceanbase", "oceanbase-ce"]:
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
    for comp in ['obproxy', 'obproxy-ce']:
        if comp in cluster_config.depends:
            obproxy_servers = cluster_config.get_depend_servers(comp)
            obproxy_server = obproxy_servers[0]
            obproxy_server_config = cluster_config.get_depend_config(comp, obproxy_server)
            depend_info['server_ip'] = obproxy_server.ip
            depend_info['mysql_port'] = obproxy_server_config['listen_port']
            break
    if 'obagent' in cluster_config.depends:
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
                    server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'], depend_info['mysql_port'], depend_info['ocp_meta_db'])
                else:
                    server_config['connect_infos'] = depend_info.get('connect_infos')
                    server_config['ocp_meta_db'] = depend_info.get('ocp_meta_db')
                    server_config['jdbc_url'] = ''
            if 'jdbc_username' in missed_keys and depend_observer:
                server_config['jdbc_username'] = "{}@{}".format(depend_info['ocp_meta_username'],
                    depend_info.get('ocp_meta_tenant', {}).get("tenant_name"))
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


def start(plugin_context, start_env=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    added_components = cluster_config.get_deploy_added_components()

    if not start_env:
        start_env = prepare_parameters(cluster_config, stdio)
        if not start_env:
            return plugin_context.return_false()



    exclude_keys = ["home_path", "port", "jdbc_url", "jdbc_username", "jdbc_password", "cluster_name", "ob_cluster_id",
                    "root_sys_password", "server_addresses", "agent_username", "agent_password", "memory_size"]

    repository_dir = None
    for repository in plugin_context.repositories:
        if repository.name == cluster_config.name:
            repository_dir = repository.repository_dir
            break
    with FileUtil.open(os.path.join(repository_dir, 'conf/ocp-express-config-mapper.yaml')) as f:
        data = YamlLoader(stdio=stdio).load(f)
    config_mapper = data.get('config_mapper', {})
    server_pid = {}
    success = True
    stdio.start_loading("Start ocp-express")
    for server in cluster_config.servers:
        client = clients[server]
        server_config = start_env[server]
        home_path = server_config['home_path']
        jdbc_url = server_config['jdbc_url']
        jdbc_username = server_config['jdbc_username']
        jdbc_password = server_config['jdbc_password']
        port = server_config['port']
        pid_path = os.path.join(home_path, 'run/ocp-express.pid')
        pids = client.execute_command("cat %s" % pid_path).stdout.strip()
        bootstrap_flag = client.execute_command('ls %s' % os.path.join(home_path, '.bootstrapped'))
        if pids and all([client.execute_command('ls /proc/%s' % pid) for pid in pids.split('\n')]):
            server_pid[server] = pids
            continue
        if getattr(options, 'without_parameter', False) and bootstrap_flag:
            use_parameter = False
        else:
            use_parameter = True
        # check meta db connect before start
        if jdbc_url:
            matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
            if not matched:
                stdio.error("Invalid jdbc url: %s" % jdbc_url)
                return
            ip = matched.group(1)
            sql_port = matched.group(2)[1:]
            database = matched.group(3)
            connect_infos = [[ip, sql_port]]
        else:
            connect_infos = server_config.get('connect_infos', '')
            database = server_config.get('ocp_meta_db', '')
        connected = False
        retries = 300
        tenant_map = {'meta@ocp_meta': {'user': 'meta@ocp', 'database': 'ocp_express'}, 'meta@ocp': {'user': 'meta@ocp_meta', 'database': 'ocp_meta'}}
        while not connected and retries:
            for connect_info in connect_infos:
                retries -= 1
                server_ip = connect_info[0]
                server_port = connect_info[-1]
                try:
                    ob_cursor = Cursor(ip=server_ip, port=server_port, user=jdbc_username, password=jdbc_password, stdio=stdio)
                    jdbc_url = 'jdbc:oceanbase://{}:{}/{}'.format(server_ip, server_port, database)
                    connected = True
                    if 'ocp-express' in added_components:
                        if ob_cursor.execute("select * from config_properties limit 1", exc_level='verbose'):
                            if not ob_cursor.execute("update config_properties set `value`=NULL, default_value=NULL where `key`='ocp.version' or `key`='ocp.version.full'", exc_level='verbose'):
                                stdio.verbose("failed to update 'ocp.version' and 'ocp.version.full' to NULL in config_properties table")
                        if ob_cursor.execute("select * from user limit 1", exc_level='verbose'):
                            if not ob_cursor.execute("update user set need_change_password=true where id='100'", exc_level='verbose'):
                                stdio.verbose("failed to update 'need_change_password' to true in user table")     
                    break
                except:
                    if tenant_map.get(jdbc_username, {}):
                        database = tenant_map.get(jdbc_username, {}).get('database')
                        jdbc_username = tenant_map.get(jdbc_username, {}).get('user')
                    time.sleep(1)
        if not connected:
            success = False
            stdio.error("{}: failed to connect meta db".format(server))
            continue

        if server_config.get('encrypt_password', False):
            private_key, public_key = get_key(client, os.path.join(home_path, 'conf'), stdio)
            public_key_str = get_plain_public_key(public_key)
            jdbc_password = rsa_private_sign(jdbc_password, private_key)
        else:
            public_key_str = ""
        memory_size = server_config['memory_size']
        jvm_memory_option = "-Xms{0} -Xmx{0}".format(str(Capacity(Capacity(memory_size).bytes * 0.5, 0)).lower())
        java_bin = server_config['java_bin']
        client.add_env('PATH', '%s/jre/bin:' % server_config['home_path'])
        cmd = '{java_bin} -jar {jvm_memory_option} -DJDBC_URL={jdbc_url} -DJDBC_USERNAME={jdbc_username}' \
              ' -DPUBLIC_KEY={public_key} {home_path}/lib/ocp-express-server.jar --port={port}'.format(
                java_bin=java_bin,
                home_path=home_path,
                port=port,
                jdbc_url=jdbc_url,
                jdbc_username=jdbc_username,
                public_key=public_key_str,
                jvm_memory_option=jvm_memory_option
        )
        if "log_dir" not in server_config:
            log_dir = os.path.join(home_path, 'log')
        else:
            log_dir = server_config["log_dir"]
        server_config["logging_file_name"] = os.path.join(log_dir, 'ocp-express.log')
        if use_parameter:
            cmd += ' --bootstrap --progress-log={}'.format(os.path.join(log_dir, 'bootstrap.log'))
            for key in server_config:
                if key not in exclude_keys and key in config_mapper:
                    if key == 'logging_file_total_size_cap':
                        cmd += ' --with-property=ocp.logging.file.total.size.cap:{}'.format(CapacityWithB(server_config[key]))
                        continue
                    cmd += ' --with-property={}:{}'.format(config_mapper[key], server_config[key])
        elif not bootstrap_flag:
            cmd += ' --bootstrap --progress-log={}'.format(os.path.join(log_dir, 'bootstrap.log'))
        data = {
            "cluster": {
                "name": server_config["cluster_name"],
                "obClusterId": server_config["ob_cluster_id"],
                "rootSysPassword": server_config["root_sys_password"],
                "serverAddresses": server_config["server_addresses"],
            },
            "agentUsername": server_config["agent_username"],
            "agentPassword": server_config["agent_password"],
            "agentAuthType": "OCP_DIGEST"
        }

        admin_passwd = cluster_config.get_global_conf_with_default().get("admin_passwd", '')

        client.add_env('OCP_EXPRESS_INIT_PROPERTIES',  json.dumps(data) if client._is_local else ConfigUtil.passwd_format(json.dumps(data)), rewrite=True)
        client.add_env('OCP_EXPRESS_ADMIN_PASSWD', admin_passwd if client._is_local else ConfigUtil.passwd_format(admin_passwd), rewrite=True)
        client.add_env('JDBC_PASSWORD', jdbc_password if client._is_local else ConfigUtil.passwd_format(jdbc_password), rewrite=True)

        client.execute_command("cd {}; bash -c '{} > /dev/null 2>&1 &'".format(home_path, cmd))
        ret = client.execute_command("ps -aux | grep '%s' | grep -v grep | awk '{print $2}' " % cmd)
        if ret:
            server_pid[server] = ret.stdout.strip()
            if not server_pid[server]:
                stdio.error("failed to start {} ocp express".format(server))
                success = False
                continue
            client.write_file(server_pid[server], os.path.join(home_path, 'run/ocp-express.pid'))
    if success:
        stdio.stop_loading('succeed')
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.start_loading("ocp-express program health check")
    failed = []
    servers = cluster_config.servers
    count = 300
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            stdio.verbose('%s program health check' % server)
            pids_stat = {}
            for pid in server_pid[server].split("\n"):
                pids_stat[pid] = None
                if not client.execute_command('ls /proc/{}'.format(pid)):
                    pids_stat[pid] = False
                    continue
                confirm = confirm_port(client, pid, int(server_config["port"]), stdio)
                if confirm:
                    pids_stat[pid] = True
                    break
            if any(pids_stat.values()):
                for pid in pids_stat:
                    if pids_stat[pid]:
                        stdio.verbose('%s ocp-express[pid: %s] started', server, pid)
                continue
            if all([stat is False for stat in pids_stat.values()]):
                failed.append('failed to start {} ocp-express'.format(server))
            elif count:
                tmp_servers.append(server)
                stdio.verbose('failed to start %s ocp-express, remaining retries: %d' % (server, count))
            else:
                failed.append('failed to start {} ocp-express'.format(server))
        servers = tmp_servers
        if servers and count:
            time.sleep(3)
    if failed:
        stdio.stop_loading('failed')
        for msg in failed:
            stdio.error(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.set_variable('start_env', start_env)
        plugin_context.return_true(need_bootstrap=True)

    return False

