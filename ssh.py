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
from paramiko.ssh_exception import NoValidConnectionsError, SSHException

from tool import DirectoryUtil


__all__ = ("SshClient", "SshConfig", "LocalClient")


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
        if LocalClient.execute_command('mkdir -p %s && cp -f %s %s' % (os.path.dirname(remote_path), local_path, remote_path), stdio=stdio):
            return True
        return False

    @staticmethod
    def put_dir(local_dir, remote_dir, stdio=None):
        if LocalClient.execute_command('mkdir -p %s && cp -fr %s %s' % (remote_dir, os.path.join(local_dir, '*'), remote_dir), stdio=stdio):
            return True
        return False

    @staticmethod
    def get_file(local_path, remote_path, stdio=None):
        return LocalClient.put_file(remote_path, local_path, stdio=stdio)

    @staticmethod
    def get_dir(local_path, remote_path, stdio=None):
        return LocalClient.put_dir(remote_path, local_path, stdio=stdio)


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
            self.is_connected = True
        except AuthenticationException:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'critical', print)('%s@%s username or password error' % (self.config.username, self.config.host))
        except NoValidConnectionsError:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'critical', print)('%s@%s connect failed: time out' % (self.config.username, self.config.host))
        except Exception as e:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'critical', print)('%s@%s connect failed: %s' % (self.config.username, self.config.host, e))
        return self.is_connected

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

    def _execute_command(self, command, retry, stdio):
        if not self._login(stdio):
            return SshReturn(255, '', 'connect failed')
            
        stdio = stdio if stdio else self.stdio
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode(errors='replace')
            error = stderr.read().decode(errors='replace')
            if output:
                idx = output.rindex('\n')
                code = int(output[idx:])
                stdout = output[:idx]
                verbose_msg = 'exited code %s' % code
            else:
                code, stdout = 1, ''
            if code:
                verbose_msg = 'exited code %s, error output:\n%s' % (code, error)
            stdio and getattr(stdio, 'verbose', print)(verbose_msg)
            return SshReturn(code, stdout, error)
        except SSHException as e:
            if retry:
                self.close()
                return self._execute_command(command, retry-1, stdio)
            else:
                stdio and getattr(stdio, 'exception', print)('')
                stdio and getattr(stdio, 'critical', print)('%s@%s connect failed: %s' % (self.config.username, self.config.host, e))
                raise e
        except Exception as e:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'critical', print)('%s@%s connect failed: %s' % (self.config.username, self.config.host, e))
            raise e
        
    def execute_command(self, command, stdio=None):
        if self._is_local():
            return LocalClient.execute_command(command, self.env, self.config.timeout, stdio=stdio)

        stdio = stdio if stdio else self.stdio
        verbose_msg = '%s execute: %s ' % (self.config, command)
        stdio and getattr(stdio, 'verbose', print)(verbose_msg, end='')
        command = '%s %s;echo -e "\n$?\c"' % (self.env_str, command.strip(';'))
        return self._execute_command(command, 3, stdio=stdio)

    def put_file(self, local_path, remote_path, stdio=None):
        stdio = stdio if stdio else self.stdio
        if not os.path.isfile(local_path):
            stdio and getattr(stdio, 'error', print)('%s is not file' % local_path)
            return False
        if self._is_local():
            return LocalClient.put_file(local_path, remote_path, stdio=stdio)
        if not self._open_sftp(stdio):
            return False
        return self._put_file(local_path, remote_path, stdio=stdio)

    def _put_file(self, local_path, remote_path, stdio=None):
        if self.execute_command('mkdir -p %s && rm -fr %s' % (os.path.dirname(remote_path), remote_path), stdio=stdio):
            stdio and getattr(stdio, 'verbose', print)('send %s to %s' % (local_path, remote_path))
            if self.sftp.put(local_path, remote_path):
                return self.execute_command('chmod %s %s' % (oct(os.stat(local_path).st_mode)[-3: ], remote_path))
        return False

    def put_dir(self, local_dir, remote_dir, stdio=None):
        stdio = stdio if stdio else self.stdio
        if self._is_local():
            return LocalClient.put_dir(local_dir, remote_dir, stdio=stdio)
        if not self._open_sftp(stdio):
            return False
        if not self.execute_command('mkdir -p %s' % remote_dir, stdio=stdio):
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
                    if not self._put_file(local_path, remote_path, stdio=stdio):
                        failed.append(remote_path)
                for name in dirs:
                    local_path = os.path.join(root, name)
                    remote_path = os.path.join(remote_dir, root[local_dir_path_len:].lstrip('/'), name)
                    if not self.execute_command('mkdir -p %s' % remote_path, stdio=stdio):
                        failed_dirs.append(local_dir)
                        failed.append(remote_path)

        for path in failed:
            stdio and getattr(stdio, 'error', print)('send %s to %s@%s failed' % (path, self.config.username, self.config.host))
        return True

    def get_file(self, local_path, remote_path, stdio=None):
        stdio = stdio if stdio else self.stdio
        dirname, _ = os.path.split(local_path)
        if not dirname:
            dirname = os.getcwd()
            local_path = os.path.join(dirname, local_path)
        if os.path.exists(dirname):
            if not os.path.isdir(dirname):
                stdio and getattr(stdio, 'error', print)('%s is not directory' % dirname)
                return False
        elif not DirectoryUtil.mkdir(dirname, stdio=stdio):
            return False
        if os.path.exists(local_path) and not os.path.isfile(local_path):
            stdio and getattr(stdio, 'error', print)('%s is not file' % local_path)
            return False
        if self._is_local():
            return LocalClient.get_file(local_path, remote_path, stdio=stdio)
        if not self._open_sftp(stdio):
            return False
        return self._get_file(local_path, remote_path, stdio=stdio)

    def _get_file(self, local_path, remote_path, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('get %s to %s' % (remote_path, local_path))
        try:
            self.sftp.get(remote_path, local_path)
            stat = self.sftp.stat(remote_path)
            os.chmod(local_path, stat.st_mode)
            return True
        except Exception as e:
            stdio and getattr(stdio, 'exception', print)('from %s@%s get %s to %s failed: %s' % (self.config.username, self.config.host, remote_path, local_path, e))
        return False

    def get_dir(self, local_dir, remote_dir, stdio=None):
        stdio = stdio if stdio else self.stdio
        dirname, _ = os.path.split(local_dir)
        if not dirname:
            dirname = os.getcwd()
            local_dir = os.path.join(dirname, local_dir)
        if os.path.exists(dirname):
            if not os.path.isdir(dirname):
                stdio and getattr(stdio, 'error', print)('%s is not directory' % dirname)
                return False
        elif not DirectoryUtil.mkdir(dirname, stdio=stdio):
            return False
        if os.path.exists(local_dir) and not os.path.isdir(local_dir):
            stdio and getattr(stdio, 'error', print)('%s is not directory' % local_dir)
            return False
        if self._is_local():
            return LocalClient.get_dir(local_dir, remote_dir, stdio=stdio)
        if not self._open_sftp(stdio):
            return False
        return self._get_dir(local_dir, remote_dir, stdio=stdio)

    def _get_dir(self, local_dir, remote_dir, failed=[], stdio=None):
        if DirectoryUtil.mkdir(local_dir, stdio=stdio):
            try:
                for fn in self.sftp.listdir(remote_dir):
                    remote_path = os.path.join(remote_dir, fn)
                    local_path = os.path.join(local_dir, fn)
                    if self.execute_command('bash -c "if [ -f %s ]; then exit 0; else exit 1; fi;"' % remote_path):
                        if not self._get_file(local_path, remote_path, stdio=stdio):
                            failed.append(remote_path)
                    else:
                        self._get_dir(local_path, remote_path, failed=failed, stdio=stdio.sub_io())
            except Exception as e:
                stdio and getattr(stdio, 'exception', print)('Fail to get %s: %s' % (remote_dir, e))
                failed.append(remote_dir)
        else:
            failed.append(remote_dir)
        return not failed

