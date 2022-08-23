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

import enum
import getpass
import os
import warnings
from glob import glob

from subprocess32 import Popen, PIPE

# paramiko import cryptography 模块在python2下会报不支持警报
warnings.filterwarnings("ignore")

from paramiko import AuthenticationException, SFTPClient
from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import NoValidConnectionsError, SSHException

from multiprocessing.queues import Empty
from multiprocessing import Queue, Process
from multiprocessing.pool import ThreadPool

from tool import COMMAND_ENV, DirectoryUtil
from _stdio import SafeStdio


__all__ = ("SshClient", "SshConfig", "LocalClient", "ConcurrentExecutor")


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


class FutureSshReturn(SshReturn):

    def __init__(self, client, command, timeout=None, stdio=None):
        self.client = client
        self.command = command
        self.timeout = timeout
        self.stdio = stdio if stdio else client.stdio
        if self.stdio:
            self.stdio = self.stdio.sub_io()
        self.finsh = False
        super(FutureSshReturn, self).__init__(127, '', '')

    def set_return(self, ssh_return):
        self.code = ssh_return.code
        self.stdout = ssh_return.stdout
        self.stderr = ssh_return.stderr
        self.finsh = True


class ConcurrentExecutor(object):

    def __init__(self, workers=None):
        self.workers = workers
        self.futures = []

    def add_task(self, client, command, timeout=None, stdio=None):
        ret = FutureSshReturn(client, command, timeout, stdio=stdio)
        self.futures.append(ret)
        return ret

    @staticmethod
    def execute(future):
        client = SshClient(future.client.config, future.stdio)
        future.set_return(client.execute_command(future.command, timeout=future.timeout))
        return future

    def submit(self):
        rets = []
        pool = ThreadPool(processes=self.workers)
        try:
            results = pool.map(ConcurrentExecutor.execute, tuple(self.futures))
            for r in results:
                rets.append(r)
        finally:
            pool.close()
        self.futures = []
        return rets


class LocalClient(SafeStdio):

    @staticmethod
    def execute_command(command, env=None, timeout=None, stdio=None):
        stdio.verbose('local execute: %s ' % command, end='')
        try:
            p = Popen(command, env=env, shell=True, stdout=PIPE, stderr=PIPE)
            output, error = p.communicate(timeout=timeout)
            code = p.returncode
            output = output.decode(errors='replace')
            error = error.decode(errors='replace')
            verbose_msg = 'exited code %s' % code
            if code:
                verbose_msg += ', error output:\n%s' % error
            stdio.verbose(verbose_msg)
        except Exception as e:
            output = ''
            error = str(e)
            code = 255
            verbose_msg = 'exited code 255, error output:\n%s' % error
            stdio.verbose(verbose_msg)
            stdio.exception('')
        return SshReturn(code, output, error)

    @staticmethod
    def put_file(local_path, remote_path, stdio=None):
        if LocalClient.execute_command('mkdir -p %s && cp -f %s %s' % (os.path.dirname(remote_path), local_path, remote_path), stdio=stdio):
            return True
        return False

    @staticmethod
    def put_dir(local_dir, remote_dir, stdio=None):
        if os.path.isdir(local_dir):
            local_dir = os.path.join(local_dir, '*')
        if os.path.exists(os.path.dirname(local_dir)) and not glob(local_dir):
            stdio.verbose("%s is empty" % local_dir)
            return True
        if LocalClient.execute_command('mkdir -p %s && cp -fr %s %s' % (remote_dir, local_dir, remote_dir), stdio=stdio):
            return True
        return False

    @staticmethod
    def get_file(local_path, remote_path, stdio=None):
        return LocalClient.put_file(remote_path, local_path, stdio=stdio)

    @staticmethod
    def get_dir(local_path, remote_path, stdio=None):
        return LocalClient.put_dir(remote_path, local_path, stdio=stdio)


class RemoteTransporter(enum.Enum):
    CLIENT = 0
    RSYNC = 1

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value


class SshClient(SafeStdio):

    def __init__(self, config, stdio=None):
        self.config = config
        self.stdio = stdio
        self.sftp = None
        self.is_connected = False
        self.ssh_client = SSHClient()
        self.env_str = ''
        self._remote_transporter = None
        self.task_queue = None
        self.result_queue = None
        if self._is_local():
            self.env = COMMAND_ENV.copy()
        else:
            self.env = {'PATH': '/sbin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:'}
            self._update_env()
        super(SshClient, self).__init__()

    def _init_queue(self):
        self.task_queue = Queue()
        self.result_queue = Queue()

    def _update_env(self):
        env = []
        for key in self.env:
            if self.env[key]:
                env.append('export %s=%s$%s;' % (key, self.env[key], key))
        self.env_str = ''.join(env)

    def add_env(self, key, value, rewrite=False, stdio=None):
        if key not in self.env or not self.env[key] or rewrite:
            stdio.verbose('%s@%s set env %s to \'%s\'' % (self.config.username, self.config.host, key, value))
            self.env[key] = value
        else:
            stdio.verbose('%s@%s append \'%s\' to %s' % (self.config.username, self.config.host, value, key))
            self.env[key] += value
        self._update_env()

    def get_env(self, key, stdio=None):
        return self.env[key] if key in self.env else None

    def del_env(self, key,  stdio=None):
        if key in self.env:
            stdio.verbose('%s@%s delete env %s' % (self.config.username, self.config.host, key))
            del self.env[key]
            self._update_env()
    
    def __str__(self):
        return '%s@%s:%d' % (self.config.username, self.config.host, self.config.port)

    def _is_local(self):
        return self.is_localhost() and self.config.username ==  getpass.getuser()

    def is_localhost(self, stdio=None):
        return self.config.host in ['127.0.0.1', 'localhost', '127.1', '127.0.1']

    def _login(self, stdio=None):
        if self.is_connected:
            return True
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
            stdio.exception('')
            stdio.critical('%s@%s username or password error' % (self.config.username, self.config.host))
        except NoValidConnectionsError:
            stdio.exception('')
            stdio.critical('%s@%s connect failed: time out' % (self.config.username, self.config.host))
        except Exception as e:
            stdio.exception('')
            stdio.critical('%s@%s connect failed: %s' % (self.config.username, self.config.host, e))
        return self.is_connected

    def _open_sftp(self, stdio=None):
        if self.sftp:
            return True
        if self._login(stdio=stdio):
            SFTPClient.from_transport(self.ssh_client.get_transport())
            self.sftp = self.ssh_client.open_sftp()
            return True
        return False

    def connect(self, stdio=None):
        if self._is_local():
            return True
        return self._login(stdio=stdio)

    def reconnect(self, stdio=None):
        self.close(stdio=stdio)
        return self.connect(stdio=stdio)

    def close(self, stdio=None):
        if self._is_local():
            return True
        if self.is_connected:
            self.ssh_client.close()
        if self.sftp:
            self.sftp = None

    def __del__(self):
        self.close()

    def _execute_command(self, command, timeout=None, retry=3, stdio=None):
        if not self._login(stdio):
            return SshReturn(255, '', 'connect failed')
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
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
            stdio.verbose(verbose_msg)
            return SshReturn(code, stdout, error)
        except SSHException as e:
            if retry:
                self.close()
                return self._execute_command(command, retry-1, stdio)
            else:
                stdio.exception('')
                stdio.critical('%s@%s connect failed: %s' % (self.config.username, self.config.host, e))
                raise e
        except Exception as e:
            stdio.exception('')
            stdio.critical('%s@%s connect failed: %s' % (self.config.username, self.config.host, e))
            raise e

    def execute_command(self, command, timeout=None, stdio=None):
        if timeout is None:
            timeout = self.config.timeout
        elif timeout <= 0:
            timeout = None
        if self._is_local():
            return LocalClient.execute_command(command, self.env, timeout, stdio=stdio)

        verbose_msg = '%s execute: %s ' % (self.config, command)
        stdio.verbose(verbose_msg, end='')
        command = '%s %s;echo -e "\n$?\c"' % (self.env_str, command.strip(';'))
        return self._execute_command(command, retry=3, timeout=timeout, stdio=stdio)

    @property
    def disable_rsync(self):
        return COMMAND_ENV.get("OBD_DISABLE_RSYNC") == "1"

    @property
    def remote_transporter(self):
        if self._remote_transporter is not None:
            return self._remote_transporter
        _transporter = RemoteTransporter.CLIENT
        if not self._is_local() and self._remote_transporter is None:
            if not self.config.password and not self.disable_rsync:
                ret = LocalClient.execute_command('rsync -h', stdio=self.stdio)
                if ret:
                    _transporter = RemoteTransporter.RSYNC
        self._remote_transporter = _transporter
        self.stdio.verbose("current remote_transporter {}".format(self._remote_transporter))
        return self._remote_transporter

    def put_file(self, local_path, remote_path, stdio=None):
        if not os.path.isfile(local_path):
            stdio.error('path: %s is not file' % local_path)
            return False
        if self._is_local():
            return LocalClient.put_file(local_path, remote_path, stdio=stdio)
        if not self._open_sftp(stdio=stdio):
            return False
        return self._put_file(local_path, remote_path, stdio=stdio)

    @property
    def _put_file(self):
        if self.remote_transporter == RemoteTransporter.RSYNC:
            return self._rsync_put_file
        else:
            return self._client_put_file

    def _client_put_file(self, local_path, remote_path, stdio=None):
        if self.execute_command('mkdir -p %s && rm -fr %s' % (os.path.dirname(remote_path), remote_path), stdio=stdio):
            stdio.verbose('send %s to %s' % (local_path, remote_path))
            if self.sftp.put(local_path, remote_path):
                return self.execute_command('chmod %s %s' % (oct(os.stat(local_path).st_mode)[-3:], remote_path))
        return False

    def _rsync(self, source, target, stdio=None):
        identity_option = ""
        if self.config.key_filename:
            identity_option += '-e "ssh -i {key_filename} "'.format(key_filename=self.config.key_filename)
        cmd = 'rsync -a -W {identity_option} {source} {target}'.format(
            identity_option=identity_option,
            source=source,
            target=target
        )
        ret = LocalClient.execute_command(cmd, stdio=stdio)
        return bool(ret)

    def _rsync_put_dir(self, local_path, remote_path, stdio=None):
        stdio.verbose('send %s to %s by rsync' % (local_path, remote_path))
        source = os.path.join(local_path, '*')
        if os.path.exists(os.path.dirname(source)) and not glob(source):
            stdio.verbose("%s is empty" % source)
            return True
        target = "{user}@{host}:{remote_path}".format(user=self.config.username, host=self.config.host, remote_path=remote_path)
        if self._rsync(source, target, stdio=stdio):
            return True
        else:
            return False

    def _rsync_put_file(self, local_path, remote_path, stdio=None):
        if not self.execute_command('mkdir -p %s' % os.path.dirname(remote_path), stdio=stdio):
            return False
        stdio.verbose('send %s to %s by rsync' % (local_path, remote_path))
        target = "{user}@{host}:{remote_path}".format(user=self.config.username, host=self.config.host, remote_path=remote_path)
        if self._rsync(local_path, target, stdio=stdio):
            return True
        else:
            return False

    def put_dir(self, local_dir, remote_dir, stdio=None):
        if self._is_local():
            return LocalClient.put_dir(local_dir, remote_dir, stdio=stdio)
        if not self._open_sftp(stdio=stdio):
            return False
        if not self.execute_command('mkdir -p %s' % remote_dir, stdio=stdio):
            return False
        stdio.start_loading('Send %s to %s' % (local_dir, remote_dir))
        ret = self._put_dir(local_dir, remote_dir, stdio=stdio)
        stdio.stop_loading('succeed' if ret else 'fail')
        return ret

    @property
    def _put_dir(self):
        if self.remote_transporter == RemoteTransporter.RSYNC:
            return self._rsync_put_dir
        else:
            return self._client_put_dir

    def _client_put_dir(self, local_dir, remote_dir, stdio=None):
        self._init_queue()
        has_failed = False
        ret = LocalClient.execute_command('find %s -type f' % local_dir)
        if not ret:
            has_failed = True
        all_files = ret.stdout.strip().split('\n') if ret.stdout else []
        ret = LocalClient.execute_command('find %s -type d' % local_dir)
        if not ret:
            has_failed = True
        all_dirs = ret.stdout.strip().split('\n') if ret.stdout else []
        self._filter_dir_in_file_path(all_files, all_dirs)
        for local_path in all_files:
            self.task_queue.put((local_path, False))
        for local_path in all_dirs:
            self.task_queue.put((local_path, True))
        length = len(all_files) + len(all_dirs)
        process_num = min(10, length)
        stdio.verbose('process num {}'.format(process_num))
        plist = []
        for _ in range(process_num):
            p = Process(target=self.file_uploader, kwargs={
                "local_dir": local_dir, "remote_dir": remote_dir,
                "stdio": stdio.sub_io()})
            p.start()
            plist.append(p)
        [p.join() for p in plist]
        return self.result_queue.qsize() == length and not has_failed

    def get_file(self, local_path, remote_path, stdio=None):
        dirname, _ = os.path.split(local_path)
        if not dirname:
            dirname = os.getcwd()
            local_path = os.path.join(dirname, local_path)
        if os.path.exists(dirname):
            if not os.path.isdir(dirname):
                stdio.error('%s is not directory' % dirname)
                return False
        elif not DirectoryUtil.mkdir(dirname, stdio=stdio):
            return False
        if os.path.exists(local_path) and not os.path.isfile(local_path):
            stdio.error('path: %s is not file' % local_path)
            return False
        if self._is_local():
            return LocalClient.get_file(local_path, remote_path, stdio=stdio)
        if not self._open_sftp(stdio=stdio):
            return False
        return self._get_file(local_path, remote_path, stdio=stdio)

    @property
    def _get_file(self):
        if self.remote_transporter == RemoteTransporter.RSYNC:
            return self._rsync_get_file
        else:
            return self._client_get_file

    def _rsync_get_dir(self, local_path, remote_path, stdio=None):
        source = "{user}@{host}:{remote_path}".format(user=self.config.username, host=self.config.host, remote_path=remote_path)
        if "*" not in remote_path:
            source = os.path.join(source, "*")
        target = local_path
        stdio.verbose('get %s from %s by rsync' % (local_path, remote_path))
        if LocalClient.execute_command('mkdir -p {}'.format(local_path), stdio=stdio) and self._rsync(source, target, stdio=stdio):
            return True
        else:
            return False

    def _rsync_get_file(self, local_path, remote_path, stdio=None):
        source = "{user}@{host}:{remote_path}".format(user=self.config.username, host=self.config.host, remote_path=remote_path)
        target = local_path
        stdio.verbose('get %s from %s by rsync' % (local_path, remote_path))
        if self._rsync(source, target, stdio=stdio):
            return True
        else:
            return False

    def _client_get_file(self, local_path, remote_path, stdio=None):
        try:
            self.sftp.get(remote_path, local_path)
            stat = self.sftp.stat(remote_path)
            os.chmod(local_path, stat.st_mode)
            return True
        except Exception as e:
            stdio.exception('get %s from %s@%s:%s failed: %s' % (local_path, self.config.username, self.config.host, remote_path, e))
        return False

    def get_dir(self, local_dir, remote_dir, stdio=None):
        dirname, _ = os.path.split(local_dir)
        if not dirname:
            dirname = os.getcwd()
            local_dir = os.path.join(dirname, local_dir)
        if "*" in dirname:
            stdio.error('Invalid directory {}'.format(dirname))
            return False
        if os.path.exists(dirname):
            if not os.path.isdir(dirname):
                stdio.error('%s is not directory' % dirname)
                return False
        elif not DirectoryUtil.mkdir(dirname, stdio=stdio):
            return False
        if os.path.exists(local_dir) and not os.path.isdir(local_dir):
            stdio.error('%s is not directory' % local_dir)
            return False
        if self._is_local():
            return LocalClient.get_dir(local_dir, remote_dir, stdio=stdio)
        if not self._open_sftp(stdio=stdio):
            return False
        stdio.start_loading('Get %s from %s' % (local_dir, remote_dir))
        ret = self._get_dir(local_dir, remote_dir, stdio=stdio)
        stdio.stop_loading('succeed' if ret else 'fail')
        return ret

    @property
    def _get_dir(self):
        if self.remote_transporter == RemoteTransporter.RSYNC:
            return self._rsync_get_dir
        else:
            return self._client_get_dir

    def _client_get_dir(self, local_dir, remote_dir, stdio=None):
        self._init_queue()
        has_failed = False
        if DirectoryUtil.mkdir(local_dir, stdio=stdio):
            try:
                ret = self.execute_command('find %s -type f' % remote_dir)
                if not ret:
                    stdio.verbose(ret.stderr)
                    has_failed = True
                all_files = ret.stdout.strip().split('\n') if ret.stdout else []
                ret = self.execute_command('find %s -type d' % remote_dir)
                if not ret:
                    has_failed = True
                all_dirs = ret.stdout.strip().split('\n') if ret.stdout else []
                self._filter_dir_in_file_path(all_files, all_dirs)
                for f in all_files:
                    self.task_queue.put(f)
                process_num = min(10, len(all_files))
                stdio.verbose('process num {}'.format(process_num))
                plist = []
                if "*" in remote_dir:
                    remote_base_dir = os.path.dirname(remote_dir)
                else:
                    remote_base_dir = remote_dir
                for _ in range(process_num):
                    p = Process(target=self.file_downloader, kwargs={
                        "local_dir": local_dir, "remote_dir": remote_base_dir, "stdio": stdio.sub_io()})
                    p.start()
                    plist.append(p)
                [p.join() for p in plist]
                for remote_path in all_dirs:
                    try:
                        local_path = os.path.join(local_dir, os.path.relpath(remote_path, remote_base_dir))
                        if not os.path.exists(local_path):
                            stat = self.sftp.stat(remote_path)
                            os.makedirs(local_path, mode=stat.st_mode)
                    except Exception as e:
                        stdio.exception('Fail to make directory %s in local: %s' % (remote_path, e))
                        has_failed = True
                return self.result_queue.qsize() == len(all_files) and not has_failed
            except Exception as e:
                stdio.exception('Fail to get %s: %s' % (remote_dir, e))

    @staticmethod
    def _filter_dir_in_file_path(files, directories):
        skip_directories = []
        for path in files:
            dir_name = os.path.dirname(path)
            while dir_name not in ["/", ".", ""]:
                if dir_name in skip_directories:
                    break
                if dir_name in directories:
                    directories.remove(dir_name)
                    skip_directories.append(dir_name)
                dir_name = os.path.dirname(dir_name)

    def file_downloader(self, local_dir, remote_dir, stdio=None):
        try:
            client = SshClient(config=self.config, stdio=None)
            client._open_sftp(stdio=stdio)
            client._remote_transporter = self.remote_transporter
            while True:
                remote_path = self.task_queue.get(block=False)
                local_path = os.path.join(local_dir, os.path.relpath(remote_path, remote_dir))
                if client.get_file(local_path, remote_path, stdio=stdio):
                    self.result_queue.put(remote_path)
                else:
                    stdio.error('Fail to get %s' % remote_path)
        except Empty:
            return
        except:
            stdio.exception("")
            stdio.exception('Failed to get %s' % remote_dir)

    def file_uploader(self, local_dir, remote_dir, stdio=None):
        try:
            client = SshClient(config=self.config, stdio=None)
            client._remote_transporter = self.remote_transporter
            while True:
                local_path, is_dir = self.task_queue.get(block=False)
                remote_path = os.path.join(remote_dir, os.path.relpath(local_path, local_dir))
                if is_dir:
                    stat = oct(os.stat(local_path).st_mode)[-3:]
                    cmd = '[ -d "{remote_path}"] || (mkdir -p {remote_path}; chmod {stat} {remote_path})'.format(remote_path=remote_path, stat=stat)
                    if client.execute_command(cmd):
                        self.result_queue.put(remote_path)
                else:
                    if client.put_file(local_path, remote_path, stdio=stdio):
                        self.result_queue.put(remote_path)
                    else:
                        stdio.error('Fail to get %s' % remote_path)
        except Empty:
            return
        except:
            stdio.exception("")
            stdio.verbose('Failed to get %s' % remote_dir)
