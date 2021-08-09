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
import sys
import getpass
import warnings
from copy import deepcopy
from subprocess32 import Popen, PIPE
# paramiko import cryptography 模块在python2下会报不支持警报
warnings.filterwarnings("ignore")

from paramiko import AuthenticationException, SFTPClient
from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import NoValidConnectionsError


class SshConfig(object):


    def __init__(self, host, username='root', password=None, key_filename=None, port=22, timeout=30):
        self.host = host
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.timeout = timeout

    def __str__(self):
        return '%s@%s' % (self.username ,self.host)


class SshReturn(object):

    def __init__(self, code, stdout, stderr):
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    def __bool__(self):
        return self.code == 0
    
    def __nonzero__(self):
        return self.__bool__()


class LocalClient(object):

    @staticmethod
    def execute_command(command, env=None, timeout=None, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('local execute: %s ' % command, end='')
        try:
            p = Popen(command, env=env, shell=True, stdout=PIPE, stderr=PIPE)
            output, error = p.communicate(timeout=timeout)
            code = p.returncode
            output = output.decode(errors='replace')
            error = error.decode(errors='replace')
            verbose_msg = 'exited code %s' % code
            if code:
                verbose_msg += ', error output:\n%s' % error
            stdio and getattr(stdio, 'verbose', print)(verbose_msg)
        except Exception as e:
            output = ''
            error = str(e)
            code = 255
            verbose_msg = 'exited code 255, error output:\n%s' % error
            stdio and getattr(stdio, 'verbose', print)(verbose_msg)
            stdio and getattr(stdio, 'exception', print)('')
        return SshReturn(code, output, error)

    @staticmethod
    def put_file(local_path, remote_path, stdio=None):
        if LocalClient.execute_command('cp -f %s %s' % (local_path, remote_path), stdio=stdio):
            return True
        return False

    @staticmethod
    def put_dir(self, local_dir, remote_dir, stdio=None):
        if LocalClient.execute_command('cp -fr %s %s' % (local_dir, remote_dir), stdio=stdio):
            return True
        return False


class SshClient(object):

    def __init__(self, config, stdio=None):
        self.config = config
        self.stdio = stdio
        self.sftp = None
        self.is_connected = False
        self.ssh_client = SSHClient()
        self.env_str = ''
        if self._is_local():
            self.env = deepcopy(os.environ.copy())
        else:
            self.env = {'PATH': '/sbin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:'}
            self._update_env()

    def _update_env(self):
        env = []
        for key in self.env:
            if self.env[key]:
                env.append('export %s=%s$%s;' % (key, self.env[key], key))
        self.env_str = ''.join(env)

    def add_env(self, key, value, rewrite=False, stdio=None):
        stdio = stdio if stdio else self.stdio
        if key not in self.env or not self.env[key] or rewrite:
            stdio and getattr(stdio, 'verbose', print)('%s@%s set env %s to \'%s\'' % (self.config.username, self.config.host, key, value))
            self.env[key] = value
        else:
            stdio and getattr(stdio, 'verbose', print)('%s@%s append \'%s\' to %s' % (self.config.username, self.config.host, value, key))
            self.env[key] += value
        self._update_env()

    def get_env(self, key):
        return self.env[key] if key in self.env else None

    def __str__(self):
        return '%s@%s:%d' % (self.config.username, self.config.host, self.config.port)

    def _is_local(self):
        return self.is_localhost() and self.config.username ==  getpass.getuser()

    def is_localhost(self, stdio=None):
        return self.config.host in ['127.0.0.1', 'localhost', '127.1', '127.0.1']

    def _login(self, stdio=None):
        if self.is_connected:
            return True
        stdio = stdio if stdio else self.stdio
        try:
            self.ssh_client.set_missing_host_key_policy(AutoAddPolicy())
            self.ssh_client.connect(
                self.config.host, 
                port=self.config.port, 
                username=self.config.username, 
                password=self.config.password, 
                key_filename=self.config.key_filename, 
                timeout=self.config.timeout
            )
        except AuthenticationException:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'critical', print)('%s@%s username or password error' % (self.config.username, self.config.host))
            return False
        except NoValidConnectionsError:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'critical', print)('%s@%s connect failed: time out' % (self.config.username, self.config.host))
            return False
        except Exception as e:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'critical', print)('%s@%s connect failed: %s' % (self.config.username, self.config.host, e))
            return False
        self.is_connected = True
        return True

    def _open_sftp(self, stdio=None):
        if self.sftp:
            return True
        if self._login(stdio):
            SFTPClient.from_transport(self.ssh_client.get_transport())
            self.sftp = self.ssh_client.open_sftp()
            return True
        return False

    def connect(self, stdio=None):
        if self._is_local():
            return True
        return self._login(stdio)

    def reconnect(self, stdio=None):
        self.close(stdio)
        return self.connect(stdio)

    def close(self, stdio=None):
        if self._is_local():
            return True
        if self.is_connected:
            self.ssh_client.close()
        if self.sftp:
            self.sftp = None

    def __del__(self):
        self.close()
        
    def execute_command(self, command, stdio=None):
        if self._is_local():
            return LocalClient.execute_command(command, self.env, self.config.timeout, stdio)
        if not self._login(stdio):
            return SshReturn(255, '', 'connect failed')

        stdio = stdio if stdio else self.stdio
        verbose_msg = '%s execute: %s ' % (self.config, command)
        stdio and getattr(stdio, 'verbose', print)(verbose_msg, end='')
        command = '%s %s;echo -e "\n$?\c"' % (self.env_str, command.strip(';'))
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        output = stdout.read().decode(errors='replace')
        error = stderr.read().decode(errors='replace')
        idx = output.rindex('\n')
        code = int(output[idx:])
        verbose_msg = 'exited code %s' % code
        if code:
            verbose_msg += ', error output:\n%s' % error
        stdio and getattr(stdio, 'verbose', print)(verbose_msg)
        return SshReturn(code, output[:idx], error)
 
    def put_file(self, local_path, remote_path, stdio=None):
        stdio = stdio if stdio else self.stdio
        if self._is_local():
            return LocalClient.put_file(local_path, remote_path, stdio)
        if not os.path.isfile(local_path):
            stdio and getattr(stdio, 'critical', print)('%s is not file' % local_path)
            return False
        if not self._open_sftp(stdio):
            return False
        
        if self.execute_command('mkdir -p %s' % os.path.split(remote_path)[0], stdio):
            return self.sftp.put(local_path, remote_path)
        return False

    def put_dir(self, local_dir, remote_dir, stdio=None):
        stdio = stdio if stdio else self.stdio
        if self._is_local():
            return LocalClient.put_dir(local_dir, remote_dir, stdio)
        if not self._open_sftp(stdio):
            return False
        if not self.execute_command('mkdir -p %s' % remote_dir, stdio):
            return False

        failed = []
        failed_dirs = []
        local_dir_path_len = len(local_dir)
        for root, dirs, files in os.walk(local_dir):
            for path in failed_dirs:
                if root.find(path) == 0:
                    # 父目录已经在被标记为失败，该层可直接跳过
                    # break退出不执行else代码段
                    break
            else:
                for name in files:
                    local_path = os.path.join(root, name)
                    remote_path = os.path.join(remote_dir, root[local_dir_path_len:].lstrip('/'), name)
                    if not self.sftp.put(local_path, remote_path):
                        failed.append(remote_path)
                for name in dirs:
                    local_path = os.path.join(root, name)
                    remote_path = os.path.join(remote_dir, root[local_dir_path_len:].lstrip('/'), name)
                    if not self.execute_command('mkdir -p %s' % remote_path, stdio):
                        failed_dirs.append(local_dir)
                        failed.append(remote_path)

        for path in failed:
            stdio and getattr(stdio, 'critical', print)('send %s to %s@%s failed' % (path, self.config.username, self.config.host))
        return True

