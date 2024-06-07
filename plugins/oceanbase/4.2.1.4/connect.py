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

import sys
import time
import re
import base64
import copy
import json
import requests
import time
import traceback

from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.PublicKey import RSA
from enum import Enum
from os import path
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
from const import RSA_KEY_SIZE
if sys.version_info.major == 2:
    import MySQLdb as mysql
else:
    import pymysql as mysql

from _errno import EC_FAIL_TO_CONNECT, EC_SQL_EXECUTE_FAILED
from _stdio import SafeStdio



class OcsResponse(object):
    def __init__(self, code, data, type):
        self.code = code
        self._data = data
        self._type = type
    
    def __bool__(self):
        return self.code == 200
    
    def __getattr__(self, name):
        if self.code == 200:
            if self._data and name in self._data:
                return self._data[name]
            else:
                return None
        return None
    
    @property
    def type(self):
        return self._type

class OcsDag(object):
    class DagState(Enum):
        PENDING = 'PENDING'
        READY = 'READY'
        RUNNING = 'RUNNING'
        FAILED = 'FAILED'
        SUCCEED = 'SUCCEED'

    class Operator(Enum):
        RUN = 'RUN'
        RETRY = 'RETRY'
        ROLLBACK = 'ROLLBACK'
        CANCEL = 'CANCEL'
        PASS = 'PASS'

    def __init__(self, data):
        self._dag_id = data['dag_id']
        self._state = data['state']
        self._operator = data['operator']
        self._id = data['id'] # id 不会是0
        self._name = data['name']

    @property
    def state(self): 
        return self._state
    
    @property
    def id(self):
        return self._id
    
    @property
    def operator(self):
        return self._operator

    @property
    def name(self):
        return self._name
    
    def is_init_task(self):
        return self.name == 'Init Cluster'
    
    def is_take_over_or_rebuild(self):
        return self.name == 'Take over' or self.name == 'Rebuild CLUSTER AGENT'
    
    def is_finished(self):
        return self.state == self.DagState.SUCCEED.value or self.state == self.DagState.FAILED.value

    def is_succeed(self):
        return self.state == self.DagState.SUCCEED.value

    def is_failed(self):
        return self.state == self.DagState.FAILED.value

    def is_run(self):
        return self.operator == self.Operator.RUN.value
    
class OcsDagResponse(OcsResponse):
    def __init__(self, code, data):
        super().__init__(code, data, 'DagDetailDTO')
        self._dag = OcsDag(data)

    def __getattr__(self, name):
        if name == 'dag':
            return self._dag
        return super().__getattr__(name)
    
class OcsInfo(object):
    class Identity(Enum):
        MASTER = 'MASTER'
        FOLLOWER = 'FOLLOWER'
        SINGLE = 'SINGLE'
        CLUSTER_AGENT = 'CLUSTER AGENT'
        TAKE_OVER_MASTER = 'TAKE_OVER_MASTER'
        TAKE_OVER_FOLLOWER = 'TAKE_OVER_FOLLOWER'

    class State(Enum):
        Unknown = 0
        Starting = 1
        Running = 2
        Stopping =  3
        Stopped = 4
    
    def __init__(self, data):
        self._state = data['state']
        self._identity = data['identity']
        self._ip = data['ip']
        self._port = data['port']
        self._zone = data['version']
        self._isObExists = data['isObExists']
        
    @property
    def state(self):
        return self._state
    
    @property
    def identity(self):
        return self._identity
    
    @property
    def isObExists(self):
        return self._isObExists

class OcsInfoResponse(OcsResponse):
    def __init__(self, code, data):
        super().__init__(code, data, 'InfoDTO')
        self._info = OcsInfo(data)

    def __getattr__(self, name):
        if name == 'info':
            return self._info
        return super().__getattr__(name)
     
class OcsStatus(object):
    class State(Enum):
        STATE_PROCESS_NOT_RUNNING = 0
        STATE_PROCESS_RUNNING = 1
        STATE_CONNECTION_RESTRICTED = 2
        STATE_CONNECTION_AVAILABLE =  3

    def __init__(self, data):
        self._state = data['state']
        self._version = data['version']
        self._pid = data['pid']
        self.startAt = data['startAt']
        self._port = data['port']

    @property
    def state(self):
        return self._state

class OcsStatusResponse(OcsResponse):
    def __init__(self, code, data):
        super().__init__(code, data, 'StatusDTO')
        self._status = OcsStatus(data)

    def __getattr__(self, name):
        if name == 'status':
            return self._status
        return super().__getattr__(name)

        
class OcsCursor(SafeStdio):

    class Header:
        auth: str
        ts: str
        uri: str
        keys: bytes
        def __init__(self, auth, ts, uri, keys):
            self.auth = auth
            self.ts = ts
            self.uri = uri
            self.keys = keys

        def serialize_struct(self):
            return json.dumps({
                'auth': self.auth,
                'ts': self.ts,
                'uri': self.uri,
                'keys': base64.b64encode(self.keys).decode('utf-8')
            })



    HEADERS = {'content-type': 'application/json'}

    def __init__(self, ip, port, homepath = None, password = None, stdio=None):
        self.ip = ip
        self.port = port
        self.stdio = stdio
        self.password = password
        self.homepath = homepath
        self.socket_file = 'obshell.' + str(port) + '.sock'
        self._auth_header = None
        self._version = ""
        self.aes_key = get_random_bytes(16)
        self.aes_iv = get_random_bytes(16)

    @staticmethod
    def _encrypt(context, encrypt_key):
        key = RSA.import_key(base64.b64decode(encrypt_key))
        cipher = PKCS1_cipher.new(key)
        return base64.b64encode(cipher.encrypt(bytes(context.encode('utf8')))).decode('utf8')

    @staticmethod
    def rsa_encrypt(context, encrypt_key):
        key = RSA.import_key(base64.b64decode(encrypt_key))
        cipher = PKCS1_cipher.new(key)
        data_to_encrypt = bytes(context.encode('utf8'))
        max_chunk_size = int(RSA_KEY_SIZE / 8) - 11
        chunks = [data_to_encrypt[i:i + max_chunk_size] for i in range(0, len(data_to_encrypt), max_chunk_size)]
        encrypted_chunks = [cipher.encrypt(chunk) for chunk in chunks]
        encrypted = b''.join(encrypted_chunks)
        encoded_encrypted_chunks = base64.b64encode(encrypted).decode('utf-8')
        return encoded_encrypted_chunks

    @staticmethod
    def aes_encrypt(self, data):
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_iv)
        return base64.b64encode(cipher.encrypt(pad(bytes(data.encode('utf8')), AES.block_size))).decode('utf8')

    @property
    def auth_header(self):
        if self._auth_header is None:
            encrypt_key = self._get_secrets()
            auth_json = json.dumps({'password': self.password, 'ts': int(datetime.now().timestamp()) + 100000})
            self._auth_header = self._encrypt(auth_json, encrypt_key)
        return self._auth_header

    @property
    def version(self):
        if self._version != "":
            return self._version
        status = requests.get(self._make_url('/api/v1/status'), headers=self._make_headers())
        if status.status_code == 200:
            self._version = status.json()['data']['version']
            return self._version
        else :
            self.stdio.warn('get obshell version failed')
            return None

    def _make_headers(self, headers=None, safe=None, uri=None):
        request_headers = copy.deepcopy(self.HEADERS)
        if safe is True :
            # request_headers['X-OCS-Auth'] = self.auth_header
            if self.version >= '4.2.3':
                header = self.Header(auth=self.password, ts=str(int(datetime.now().timestamp()) + 100000), uri=uri, keys=self.aes_key+self.aes_iv)
                request_headers['X-OCS-Header'] = self.rsa_encrypt(header.serialize_struct(), self._get_secrets())
            else:
                request_headers['X-OCS-Auth'] = self.auth_header
        if headers:
            request_headers.update(headers)
        return request_headers

    def _make_url(self, url):
        return 'http://{ip}:{port}{url}'.format(ip=self.ip, port=self.port, url=url)
    
    # put new password to obshell
    def update_password(self, password):
        self.password = password
        self._auth_header = None
        # Invoke any API that requires the `safe_request` method to securely update passwords.
        self.pkg_upload_request()
        return

    def _request(self, method, url, data=None, headers=None, params=None, safe=None, ignore_ConnectionError=False, *args, **kwargs):
        try: 
            if data is not None:
                data = json.dumps(data)
            else:
                data = json.dumps({})
            if safe and self.version >= '4.2.3':
                data = self.aes_encrypt(self, data)
            self.stdio.verbose('send request to obshell: method: {}, url: {}, data: {}, headers: {}, params: {}'.format(method, url, data, headers, params))
            resp = requests.request(method, self._make_url(url), data=data, headers=self._make_headers(headers, safe, url), params=params, *args, **kwargs)
        except Exception as e:
            if ignore_ConnectionError and isinstance(e, requests.exceptions.ConnectionError):
                self.stdio.verbose('Attempt to connect failed：{}'.format(self._make_url(url)))
                return None
            self.stdio.error('request error: {}'.format(e))
            return None
        parsed_resp = self._response_parser(resp)
        if parsed_resp.code != 200:
            self.stdio.verbose('request obshell failed: {}'.format(resp))
            return None
        return parsed_resp
    
    def _curl_socket(self, ssh_client, method, url, data=None):
        if data is not None:
            data = json.dumps(data)
        socket_path = path.join(self.homepath, 'run', self.socket_file)
        cmd = 'curl --unix-socket %s -X %s -d \'%s\'  %s' % (socket_path, method, data, self._make_url(url))
        self.stdio.verbose('cmd: {}'.format(cmd))
        ssh_return = ssh_client.execute_command(cmd)
        return self._response_parser(ssh_return.stdout, is_socket=True)

    def _response_parser(self, resp, is_socket=False):
        try:
            if is_socket:
                data = json.loads(resp)
                status_code = data['status']
            else:
                data = resp.json()
                # self.stdio.print('data: {}'.format(data))
                status_code = resp.status_code
            if status_code == 200:
                if 'data' in data:
                    data = data['data']
                    if 'dag_id' in data and 'state' in data and 'operator' in data and 'id' in data: # 是不是已经足够说明返回了一个DagDetailDTO？
                        return OcsDagResponse(status_code, data)
                    if 'state' in data and 'identity' in data and 'ip' in data and 'port' in data and 'version' in data: # 返回了一个info
                        return OcsInfoResponse(status_code, data)
                    if 'state' in data and 'version' in data and 'pid' in data and 'startAt' in data and 'port' in data: # 返回了一个state
                        return OcsStatusResponse(status_code, data)
                    else:
                        return OcsResponse(status_code, data, "Unknown")
            return OcsResponse(status_code, None, None)
        except Exception as e:
            traceback.print_exc()
            self.stdio.error('response parser error: {}'.format(e))
            return None
    
    # get the public key from ocs agent
    def _get_secrets(self):
        resp = self._request('GET', '/api/v1/secret')
        return resp.public_key if resp else None
    
    def request(self, method, url, data=None, headers=None, params=None, ignore_ConnectionError=False, *args, **kwargs):
        return self._request(method, url, data, headers, params, ignore_ConnectionError=ignore_ConnectionError, *args, **kwargs)
    
    def safe_request(self, method, url, data=None, headers=None, params=None, *args, **kwargs):
        return self._request(method, url, data, headers, params, safe=True, *args, **kwargs)
    
    def query_dag_util_succeed(self, _dag):
        dag = _dag
        while True:
            if not dag:
                return False
            if dag.state == dag.DagState.SUCCEED.value:
                return True
            dag = self.get_dag_request(dag.id)
            time.sleep(1)

    def query_dag_util_finish(self, _dag):
        dag = _dag
        while True: 
            dag = self.get_dag_request(dag.id)
            if not dag:
                return None
            if dag.is_finished():
                return dag
            time.sleep(1)

    # normal route
    def info_request(self):
        resp = self.request('GET', '/api/v1/info')
        return resp.info if resp and resp.type == 'InfoDTO' else None

    def status_request(self, ignore_ConnectionError=False):
        resp = self.request('GET', '/api/v1/status', ignore_ConnectionError=ignore_ConnectionError)
        return resp.status if resp and resp.type == 'StatusDTO' else None

    def secret_request(self):
        return self.request('GET', '/api/v1/secret')

    # ob routes
    def ob_init_request(self):
        resp = self.safe_request('POST', '/api/v1/ob/init')
        return self.query_dag_util_finish(resp.dag) if resp else False
    
    def ob_stop_request(self, type = 'GLOBAL', target = None):
        resp = self.safe_request('POST', '/api/v1/ob/stop', data = {'scope': {'type': type, 'target': target}, 'force': True})
        return self.query_dag_util_finish(resp.dag) if resp else False
    
    def ob_start_request(self, type = 'GLOBAL', target = None):
        resp = self.safe_request('POST', '/api/v1/ob/start', data = {'scope': {'type': type, 'target': target}})
        return self.query_dag_util_finish(resp.dag) if resp else False
    
    def ob_info_request(self, data):
        resp = self.safe_request('POST', '/api/v1/ob/info', data=data)
        return resp

    # agent admin routes  
    def agent_join_request(self, ip, port, zone):
        resp = self.safe_request('POST', '/api/v1/agent', data={'agentInfo': {'ip': ip, 'port': port}, 'zoneName': zone})
        return self.query_dag_util_finish(resp.dag) if resp else False
    
    def agent_remove_request(self, ip, port):
        resp = self.safe_request('DELETE', '/api/v1/agent', data={'ip': ip, 'port': port})
        return self.query_dag_util_finish(resp.dag) if resp else False
    
    def agent_remove_by_socket(self, ssh_client, ip, port):
        resp = self._curl_socket(ssh_client, 'DELETE', '/api/v1/agent', data={'ip': ip, 'port': port})
        return self.query_dag_util_finish(resp.dag) if resp else False
    
    # obcluster routes
    def obcluster_config_request(self, cluster_id, cluster_name, rs_list):
        encrypt_key = self._get_secrets()
        encrypt_password = self._encrypt(self.password, encrypt_key)
        resp = self.safe_request('POST', '/api/v1/obcluster/config', data={'clusterId': cluster_id, 'clusterName': cluster_name, 'rootPwd': encrypt_password, 'rsList': rs_list})
        return self.query_dag_util_finish(resp.dag) if resp else False

    # observer routes
    def observer_put_config_request(self, server_config, agent_list, restart = True):
        # 把serverconfig中的int类型的value全部转换成string类型
        for key in server_config:
            server_config[key] = str(server_config[key])
        resp = self.safe_request('PUT', '/api/v1/observer/config', data={'observerConfig': server_config, 'restart': restart, 'scope': {'type': 'SERVER', 'target': agent_list}})
        return self.query_dag_util_finish(resp.dag) if resp else False

    # def observer_patch_config_request(self, server_config, servers, restart = False):
    #     resp = self.safe_request('POST', '/api/v1/observer/config', data={'observerConfig': server_config, 'restart': restart, 'scope': {'type': 'SERVER', 'target': servers}})
    #     return self.query_dag_util_succeed(resp.dag) if resp else False

    def observer_scale_out_request(self, ip, port, zone, server_config):
        resp = self.safe_request('POST', '/api/v1/ob/scale_out', data={'agentInfo': {'ip': ip, 'port': port}, 'obConfigs': server_config,'zone': zone})
        return self.query_dag_util_finish(resp.dag) if resp else False

    # upgrade routes
    def pkg_upload_request(self, data = None):
        return self.safe_request('POST', '/api/v1/upgrade/package', data=data)

    def params_backup_request(self, data = None):
        return self.safe_request('POST', '/api/v1/upgrade/params/backup', data=data)

    # task routes
    def get_dag_request(self, id):
        resp = self.safe_request('GET', '/api/v1/task/dag/%s' % id)
        return resp.dag if resp else None

    def dag_request(self, dag, operator):
        resp = self.safe_request('POST', '/api/v1/task/dag/%s' % dag.id, data={'operator': operator})
        if not resp:
            return False
        return self.query_dag_util_finish(dag) 
        
    def get_agent_last_maintenance_dag_request(self):
        if self.version >='4.2.3':
            resp = self.safe_request('GET', '/api/v1/task/dag/maintain/agent')
        else:
            resp = self.request('GET', '/api/v1/task/dag/maintain/agent')
        return resp.dag if resp else None

    def get_ob_last_maintenance_dag_request(self):
        if self.version >= '4.2.3':
            resp = self.safe_request('GET', '/api/v1/task/dag/maintain/ob')
        else :
            resp = self.request('GET', '/api/v1/task/dag/maintain/ob')
        return resp.dag if resp else None

def get_ocs_cursor(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    cursors = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        password = server_config.get('root_password', '')
        obshell_port = server_config.get('obshell_port')
        stdio.verbose('connect obshell ({}:{})'.format(server.ip, obshell_port))
        ocs_cursor = OcsCursor(ip=server.ip, port=obshell_port, homepath=server_config['home_path'], password=password, stdio=stdio)
        cursors[server] = ocs_cursor
    return cursors


class Cursor(SafeStdio):

    def __init__(self, ip, port, user='root', tenant='sys', password='', stdio=None):
        self.stdio = stdio
        self.ip = ip
        self.port = port
        self._user = user
        self.tenant = tenant
        self.password = password
        self.cursor = None
        self.db = None
        self._connect()
        self._raise_exception = False
        self._raise_cursor = None

    @property
    def user(self):
        if "@" in self._user:
            return self._user
        if self.tenant:
            return "{}@{}".format(self._user, self.tenant)
        else:
            return self._user

    @property
    def raise_cursor(self):
        if self._raise_cursor:
            return self._raise_cursor
        raise_cursor = copy.copy(self)
        raise_cursor._raise_exception = True
        self._raise_cursor = raise_cursor
        return raise_cursor

    if sys.version_info.major == 2:
        def _connect(self):
            self.stdio.verbose('connect %s -P%s -u%s -p%s' % (self.ip, self.port, self.user, self.password))
            self.db = mysql.connect(host=self.ip, user=self.user, port=int(self.port), passwd=str(self.password))
            self.cursor = self.db.cursor(cursorclass=mysql.cursors.DictCursor)
    else:
        def _connect(self):
            self.stdio.verbose('connect %s -P%s -u%s -p%s' % (self.ip, self.port, self.user, self.password))
            self.db = mysql.connect(host=self.ip, user=self.user, port=int(self.port), password=str(self.password),
                                    cursorclass=mysql.cursors.DictCursor)
            self.cursor = self.db.cursor()

    def new_cursor(self, tenant='sys', user='root', password='', ip='', port='', print_exception=True):
        try:
            ip = ip if ip else self.ip
            port = port if port else self.port
            return Cursor(ip=ip, port=port, user=user, tenant=tenant, password=password, stdio=self.stdio)
        except:
            print_exception and self.stdio.exception('')
            self.stdio.verbose('fail to connect %s -P%s -u%s@%s -p%s' % (self.ip, self.port, user, tenant, password))
            return None

    def execute(self, sql, args=None, execute_func=None, raise_exception=None, exc_level='error', stdio=None):

        try:
            stdio.verbose('execute sql: %s. args: %s' % (sql, args))
            self.cursor.execute(sql, args)
            if not execute_func:
                return self.cursor
            return getattr(self.cursor, execute_func)()
        except Exception as e:
            getattr(stdio, exc_level)(EC_SQL_EXECUTE_FAILED.format(sql=sql))
            pattern = r'\n\[(.*?)\]\s+\[(.*?)\]\s+\[(.*?)\]$'
            error_matches = re.findall(pattern, str(e.args[-1]))
            if len(error_matches) > 0 and len(error_matches[-1]) == 3:
                getattr(stdio, exc_level)("observer error trace [%s] from [%s]" % (error_matches[-1][2], error_matches[-1][0]))
            if raise_exception is None:
                raise_exception = self._raise_exception
            if raise_exception:
                stdio.exception('')
                raise e
            return False

    def fetchone(self, sql, args=None, raise_exception=None, exc_level='error', stdio=None):
        return self.execute(sql, args=args, execute_func='fetchone', raise_exception=raise_exception, exc_level=exc_level, stdio=stdio)

    def fetchall(self, sql, args=None, raise_exception=None, exc_level='error', stdio=None):
        return self.execute(sql, args=args, execute_func='fetchall', raise_exception=raise_exception, exc_level=exc_level, stdio=stdio)

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.db:
            self.db.close()
            self.db = None


def connect(plugin_context, target_server=None, retry_times=101, connect_all=False, *args, **kwargs):
    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)

    ocs_cursor = get_ocs_cursor(plugin_context, *args, **kwargs)
    stdio = plugin_context.stdio
    if not ocs_cursor:
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    count = retry_times
    cluster_config = plugin_context.cluster_config
    if target_server:
        servers = [target_server]
        server_config = cluster_config.get_server_conf(target_server)
        stdio.start_loading('Connect observer(%s:%s)' % (target_server, server_config['mysql_port']))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to observer')
    while count:
        count -= 1
        connect_nums = 0
        for server in servers:
            try:
                server_config = cluster_config.get_server_conf(server)
                password = server_config.get('root_password', '') if count % 2 == 0 else ''
                cursor = Cursor(ip=server.ip, port=server_config['mysql_port'], tenant='', password=password if password is not None else '', stdio=stdio)
                if cursor.execute('select 1', raise_exception=False, exc_level='verbose'):
                    if not connect_all:
                        stdio.stop_loading('succeed', text='Connect to observer {}:{}'.format(server.ip, server_config['mysql_port']))
                        return return_true(connect=cursor.db, cursor=cursor, server=server, ocs_cursor = ocs_cursor)
                    else:
                        connect_nums += 1
                        if connect_nums == len(servers):
                            stdio.stop_loading('succeed')
                            return return_true(connect=cursor.db, cursor=cursor, server=server, ocs_cursor = ocs_cursor)
                else:
                    raise Exception('Connect to observer {}:{} failed'.format(server.ip, server_config['mysql_port']))
            except:
                if count == 0:
                    stdio.exception('')
                if connect_all:
                    break
        time.sleep(3)
    
    stdio.stop_loading('fail')
    stdio.error(EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
    plugin_context.return_false()
