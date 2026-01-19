
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

import base64
import os
import bz2
import random
import sys
import stat
import gzip
import fcntl
import signal
import shutil
import re
import json
import time
import hashlib
import socket
import datetime
from io import BytesIO
from copy import copy, deepcopy

import string

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from ruamel.yaml import YAML, YAMLContextManager, representer
import _environ as ENV
import _errno
import const
from _errno import EC_SQL_EXECUTE_FAILED
from _stdio import SafeStdio, FormatText
from collections import Counter

_open = open
if sys.version_info.major == 2:
    import MySQLdb as mysql
    from collections import OrderedDict
    from backports import lzma
    from io import open as _open

    def encoding_open(path, _type, encoding=None, *args, **kwrags):
        if encoding:
            kwrags['encoding'] = encoding
            return _open(path, _type, *args, **kwrags)
        else:
            return open(path, _type, *args, **kwrags)

    class TimeoutError(OSError):

        def __init__(self, *args, **kwargs):
            super(TimeoutError, self).__init__(*args, **kwargs)

else:
    import lzma
    import pymysql as mysql
    encoding_open = open

    class OrderedDict(dict):
        pass


__all__ = ("timeout", "DynamicLoading", "ConfigUtil", "DirectoryUtil", "FileUtil", "YamlLoader", "OrderedDict", "COMMAND_ENV", "TimeUtils", "Cursor")

_WINDOWS = os.name == 'nt'

init_cx_oracle = False

class Timeout(object):

    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def _is_timeout(self):
        return self.seconds and self.seconds > 0

    def __enter__(self):
        if self._is_timeout():
            signal.signal(signal.SIGALRM, self.handle_timeout)
            signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        if self._is_timeout():
            signal.alarm(0)


timeout = Timeout


class Timeout:

    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def _is_timeout(self):
        return self.seconds and self.seconds > 0

    def __enter__(self):
        if self._is_timeout():
            signal.signal(signal.SIGALRM, self.handle_timeout)
            signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        if self._is_timeout():
            signal.alarm(0)

timeout = Timeout


class DynamicLoading(object):

    class Module(object):

        def __init__(self, module):
            self.module = module
            self.count = 0

    LIBS_PATH = {}
    MODULES = {}

    @staticmethod
    def add_lib_path(lib):
        if lib not in DynamicLoading.LIBS_PATH:
            DynamicLoading.LIBS_PATH[lib] = 0
        if DynamicLoading.LIBS_PATH[lib] == 0:
            sys.path.insert(0, lib)
        DynamicLoading.LIBS_PATH[lib] += 1

    @staticmethod
    def add_libs_path(libs):
        for lib in libs:
            DynamicLoading.add_lib_path(lib)

    @staticmethod
    def remove_lib_path(lib):
        if lib not in DynamicLoading.LIBS_PATH:
            return
        if DynamicLoading.LIBS_PATH[lib] < 1:
            return
        try:
            DynamicLoading.LIBS_PATH[lib] -= 1
            if DynamicLoading.LIBS_PATH[lib] == 0:
                idx = sys.path.index(lib)
                del sys.path[idx]
        except:
            pass

    @staticmethod
    def remove_libs_path(libs):
        for lib in libs:
            DynamicLoading.remove_lib_path(lib)

    @staticmethod
    def import_module(name, stdio=None):
        if name not in DynamicLoading.MODULES:
            try:
                stdio and getattr(stdio, 'verbose', print)('import %s' % name)
                module = __import__(name)
                DynamicLoading.MODULES[name] = DynamicLoading.Module(module)
            except:
                stdio and getattr(stdio, 'exception', print)('import %s failed' % name)
                stdio and getattr(stdio, 'verbose', print)('sys.path: %s' % sys.path)
                return None
        DynamicLoading.MODULES[name].count += 1
        stdio and getattr(stdio, 'verbose', print)('add %s ref count to %s' % (name, DynamicLoading.MODULES[name].count))
        return DynamicLoading.MODULES[name].module

    @staticmethod
    def export_module(name, stdio=None):
        if name not in DynamicLoading.MODULES:
            return
        if DynamicLoading.MODULES[name].count < 1:
            return
        try:
            DynamicLoading.MODULES[name].count -= 1
            stdio and getattr(stdio, 'verbose', print)('sub %s ref count to %s' % (name, DynamicLoading.MODULES[name].count))
            if DynamicLoading.MODULES[name].count == 0:
                stdio and getattr(stdio, 'verbose', print)('export %s' % name)
                del sys.modules[name]
                del DynamicLoading.MODULES[name]
        except:
            stdio and getattr(stdio, 'exception', print)('export %s failed' % name)


class ConfigUtil(object):

    @staticmethod
    def get_value_from_dict(conf, key, default=None, transform_func=None):
        try:
            # 不要使用 conf.get(key, default)来替换，这里还有类型转换的需求
            value = conf[key]
            return transform_func(value) if value is not None and transform_func else value
        except:
            return default

    @staticmethod
    def get_list_from_dict(conf, key, transform_func=None):
        try:
            return_list = conf[key]
            if transform_func:
                return [transform_func(value) for value in return_list]
            else:
                return return_list
        except:
            return []

    @staticmethod
    def get_random_pwd_by_total_length(pwd_length=10):
        char = string.ascii_letters + string.digits
        pwd = ""
        for i in range(pwd_length):
            pwd = pwd + random.choice(char)
        return pwd

    @staticmethod
    def get_random_pwd_by_rule(lowercase_length=2, uppercase_length=2, digits_length=2, punctuation_length=2, punctuation_chars='(._+@#%)'):
        pwd = ""
        for i in range(lowercase_length):
            pwd += random.choice(string.ascii_lowercase)
        for i in range(uppercase_length):
            pwd += random.choice(string.ascii_uppercase)
        for i in range(digits_length):
            pwd += random.choice(string.digits)
        for i in range(punctuation_length):
            pwd += random.choice(punctuation_chars)
        pwd_list = list(pwd)
        random.shuffle(pwd_list)
        return ''.join(pwd_list)

    @staticmethod
    def passwd_format(passwd):
        return "'{}'".format(passwd.replace("'", "'\"'\"'"))


class DirectoryUtil(object):

    @staticmethod
    def get_owner(path):
        return os.stat(path)[stat.ST_UID]

    @staticmethod
    def list_dir(path, stdio=None):
        files = []
        if os.path.isdir(path):
            for fn in os.listdir(path):
                fp = os.path.join(path, fn)
                if os.path.isdir(fp):
                    files += DirectoryUtil.list_dir(fp)
                else:
                    files.append(fp)
        return files

    @staticmethod
    def copy(src, dst, stdio=None):
        if not os.path.isdir(src):
            stdio and getattr(stdio, 'error', print)("cannot copy tree '%s': not a directory" % src)
            return False
        try:
            names = os.listdir(src)
        except:
            stdio and getattr(stdio, 'exception', print)("error listing files in '%s':" % (src))
            return False

        if DirectoryUtil.mkdir(dst, stdio):
            return False

        ret = True
        links = []
        for n in names:
            src_name = os.path.join(src, n)
            dst_name = os.path.join(dst, n)
            if os.path.islink(src_name):
                link_dest = os.readlink(src_name)
                links.append((link_dest, dst_name))

            elif os.path.isdir(src_name):
                ret = DirectoryUtil.copy(src_name, dst_name, stdio) and ret
            else:
                FileUtil.copy(src_name, dst_name, stdio)
        for link_dest, dst_name in links:
            directory = os.path.dirname(dst_name)
            os.makedirs(directory, exist_ok=True)
            FileUtil.symlink(link_dest, dst_name, stdio)
        return ret

    @staticmethod
    def mkdir(path, mode=0o755, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('mkdir %s' % path)
        try:
            os.makedirs(path, mode=mode)
            return True
        except OSError as e:
            if e.errno == 17:
                return True
            elif e.errno == 20:
                stdio and getattr(stdio, 'error', print)('%s is not a directory', path)
            else:
                stdio and getattr(stdio, 'error', print)('failed to create directory %s', path)
            stdio and getattr(stdio, 'exception', print)('')
        except:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'error', print)('failed to create directory %s', path)
        return False

    @staticmethod
    def rm(path, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('rm %s' % path)
        try:
            if os.path.islink(path):
                os.remove(path)
            elif os.path.exists(path):
                shutil.rmtree(path)
            else:
                pass
            return True
        except Exception as e:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'error', print)('failed to remove %s', path)
        return False


class FileUtil(object):

    COPY_BUFSIZE = 1024 * 1024 if _WINDOWS else 64 * 1024

    @staticmethod
    def checksum(target_path, stdio=None):
        from ssh import LocalClient
        if not os.path.isfile(target_path):
            info = 'No such file: ' + target_path
            if stdio:
                getattr(stdio, 'error', print)(info)
                return False
            else:
                raise IOError(info)
        ret = LocalClient.execute_command('md5sum {}'.format(target_path), stdio=stdio)
        if ret:
            return ret.stdout.strip().split(' ')[0].encode('utf-8')
        else:
            m = hashlib.md5()
            with open(target_path, 'rb') as f:
                m.update(f.read())
            return m.hexdigest().encode(sys.getdefaultencoding())

    @staticmethod
    def copy_fileobj(fsrc, fdst):
        fsrc_read = fsrc.read
        fdst_write = fdst.write
        while True:
            buf = fsrc_read(FileUtil.COPY_BUFSIZE)
            if not buf:
                break
            fdst_write(buf)

    @staticmethod
    def copy(src, dst, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('copy %s %s' % (src, dst))
        if os.path.exists(src) and os.path.exists(dst) and os.path.samefile(src, dst):
            info = "`%s` and `%s` are the same file" % (src, dst)
            if stdio:
                getattr(stdio, 'error', print)(info)
                return False
            else:
                raise IOError(info)

        for fn in [src, dst]:
            try:
                st = os.stat(fn)
            except OSError:
                pass
            else:
                if stat.S_ISFIFO(st.st_mode):
                    info = "`%s` is a named pipe" % fn
                    if stdio:
                        getattr(stdio, 'error', print)(info)
                        return False
                    else:
                        raise IOError(info)

        try:
            if os.path.islink(src):
                FileUtil.symlink(os.readlink(src), dst)
                return True
            with FileUtil.open(src, 'rb') as fsrc, FileUtil.open(dst, 'wb') as fdst:
                    FileUtil.copy_fileobj(fsrc, fdst)
                    os.chmod(dst, os.stat(src).st_mode)
                    return True
        except Exception as e:
            if int(getattr(e, 'errno', -1)) == 26:
                from ssh import LocalClient
                if LocalClient.execute_command('/usr/bin/cp -f %s %s' % (src, dst), stdio=stdio):
                    return True
            elif stdio:
                getattr(stdio, 'exception', print)('copy error: %s' % e)
            else:
                raise e
        return False

    @staticmethod
    def symlink(src, dst, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('link %s %s' % (src, dst))
        try:
            if DirectoryUtil.rm(dst, stdio):
                os.symlink(src, dst)
                return True
        except Exception as e:
            if stdio:
                getattr(stdio, 'exception', print)('link error: %s' % e)
            else:
                raise e
        return False

    @staticmethod
    def open(path, _type='r', encoding=None, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('open %s for %s' % (path, _type))
        if os.path.exists(path):
            if os.path.isfile(path):
                return encoding_open(path, _type, encoding=encoding)
            info = '%s is not file' % path
            if stdio:
                getattr(stdio, 'error', print)(info)
                return None
            else:
                raise IOError(info)
        dir_path, file_name = os.path.split(path)
        if not dir_path or DirectoryUtil.mkdir(dir_path, stdio=stdio):
            return encoding_open(path, _type, encoding=encoding)
        info = '%s is not file' % path
        if stdio:
            getattr(stdio, 'error', print)(info)
            return None
        else:
            raise IOError(info)

    @staticmethod
    def unzip(source, ztype=None, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('unzip %s' % source)
        if not ztype:
            ztype = source.split('.')[-1]
        try:
            if ztype == 'bz2':
                s_fn = bz2.BZ2File(source, 'r')
            elif ztype == 'xz':
                s_fn = lzma.LZMAFile(source, 'r')
            elif ztype == 'gz':
                s_fn = gzip.GzipFile(source, 'r')
            else:
                s_fn = open(source, 'r')
            return s_fn
        except:
            stdio and getattr(stdio, 'exception', print)('failed to unzip %s' % source)
        return None

    @staticmethod
    def rm(path, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('rm %s' % path)
        if not os.path.exists(path):
            return True
        try:
            os.remove(path)
            return True
        except:
            stdio and getattr(stdio, 'exception', print)('failed to remove %s' % path)
        return False

    @staticmethod
    def move(src, dst, stdio=None):
        return shutil.move(src, dst)

    @staticmethod
    def share_lock_obj(obj, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('try to get share lock %s' % obj.name)
        fcntl.flock(obj, fcntl.LOCK_SH | fcntl.LOCK_NB)
        return obj

    @classmethod
    def share_lock(cls, path, _type='w', stdio=None):
        return cls.share_lock_obj(cls.open(path, _type=_type, stdio=stdio))

    @staticmethod
    def exclusive_lock_obj(obj, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('try to get exclusive lock %s' % obj.name)
        fcntl.flock(obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return obj

    @classmethod
    def exclusive_lock(cls, path, _type='w', stdio=None):
        return cls.exclusive_lock_obj(cls.open(path, _type=_type, stdio=stdio))

    @staticmethod
    def unlock(obj, stdio=None):
        stdio and getattr(stdio, 'verbose', print)('unlock %s' % obj.name)
        fcntl.flock(obj, fcntl.LOCK_UN)
        return obj


class YamlLoader(YAML):

    def __init__(self, stdio=None, typ=None, pure=False, output=None, plug_ins=None):
        super(YamlLoader, self).__init__(typ=typ, pure=pure, output=output, plug_ins=plug_ins)
        self.stdio = stdio
        if not self.Representer.yaml_multi_representers and self.Representer.yaml_representers:
            self.Representer.yaml_multi_representers = self.Representer.yaml_representers

    def load(self, stream):
        try:
            return super(YamlLoader, self).load(stream)
        except Exception as e:
            if getattr(self.stdio, 'exception', False):
                self.stdio.exception('Parsing error:\n%s' % e)
            raise e

    def loads(self, yaml_content):
        try:
            stream = BytesIO()
            yaml_content = str(yaml_content).encode() if isinstance(yaml_content, str) else yaml_content
            stream.write(yaml_content)
            stream.seek(0)
            return self.load(stream)
        except Exception as e:
            if getattr(self.stdio, 'exception', False):
                self.stdio.exception('Parsing error:\n%s' % e)
            raise e

    def dump(self, data, stream=None, transform=None):
        try:
            return super(YamlLoader, self).dump(data, stream=stream, transform=transform)
        except Exception as e:
            if getattr(self.stdio, 'exception', False):
                self.stdio.exception('dump error:\n%s' % e)
            raise e

    def dumps(self, data, transform=None):
        try:
            stream = BytesIO()
            self.dump(data, stream=stream, transform=transform)
            stream.seek(0)
            content = stream.read()
            if sys.version_info.major == 2:
                return content
            return content.decode()
        except Exception as e:
            if getattr(self.stdio, 'exception', False):
                self.stdio.exception('dumps error:\n%s' % e)
            raise e


_KEYCRE = re.compile(r"\$(\w+)")


def var_replace(string, var, pattern=_KEYCRE):
    if not var:
        return string
    done = []

    while string:
        m = pattern.search(string)
        if not m:
            done.append(string)
            break

        varname = m.group(1).lower()
        replacement = var.get(varname, m.group())

        start, end = m.span()
        done.append(string[:start])
        done.append(str(replacement))
        string = string[end:]

    return ''.join(done)


class CommandEnv(SafeStdio):

    def __init__(self):
        self.source_path = None
        self._env = os.environ.copy()
        self._cmd_env = {}

    def load(self, source_path, stdio=None):
        if self.source_path:
            stdio.error("Source path of env already set.")
            return False
        self.source_path = source_path
        try:
            if os.path.exists(source_path):
                with FileUtil.open(source_path, 'r') as f:
                    self._cmd_env = json.load(f)
        except:
            stdio.exception("Failed to load environments from {}".format(source_path))
            return False
        return True

    def save(self, stdio=None):
        if self.source_path is None:
            stdio.error("Command environments need to load at first.")
            return False
        stdio.verbose("save environment variables {}".format(self._cmd_env))
        try:
            with FileUtil.open(self.source_path, 'w', stdio=stdio) as f:
                json.dump(self._cmd_env, f)
        except:
            stdio.exception('Failed to save environment variables')
            return False
        return True

    def get(self, key, default=""):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def set(self, key, value, save=False, stdio=None):
        stdio.verbose("set environment variable {} value {}".format(key, value))
        self._cmd_env[key] = str(value)
        if save:
            return self.save(stdio=stdio)
        return True

    def delete(self, key, save=False, stdio=None):
        stdio.verbose("delete environment variable {}".format(key))
        if key in self._cmd_env:
            del self._cmd_env[key]
        if save:
            return self.save(stdio=stdio)
        return True

    def clear(self, save=True, stdio=None):
        self._cmd_env = {}
        if save:
            return self.save(stdio=stdio)
        return True

    def __getitem__(self, item):
        value = self._cmd_env.get(item)
        if value is None:
            value = self._env.get(item)
        if value is None:
            raise KeyError(item)
        return value

    def __contains__(self, item):
        if item in self._cmd_env:
            return True
        elif item in self._env:
            return True
        else:
            return False

    def copy(self):
        result = dict(self._env)
        result.update(self._cmd_env)
        return result

    def show_env(self):
        return self._cmd_env


class NetUtil(object):

    @staticmethod
    def get_host_ip():
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip

    @staticmethod
    def get_all_ips():
        import netifaces
        ips = []
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:  # IPv4 address
                for addr_info in addrs[netifaces.AF_INET]:
                    ips.append(addr_info['addr'])
            if netifaces.AF_INET6 in addrs:  # IPv6 address
                for addr_info in addrs[netifaces.AF_INET6]:
                    ips.append(addr_info['addr'])
        return ips


COMMAND_ENV=CommandEnv()


class TimeUtils(SafeStdio):

    @staticmethod
    def parse_time_sec(time_str):
        unit = time_str[-1]
        value = int(time_str[:-1])
        if unit == "s":
            value *= 1
        elif unit == "m":
            value *= 60
        elif unit == "h":
            value *= 3600
        elif unit == "d":
            value *= 3600 * 24
        else:
            raise Exception('%s parse time to second fialed:' % (time_str))
        return value

    @staticmethod
    def get_format_time(time_str, stdio=None):
        try:
            return datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            stdio.exception('%s parse time fialed, error:\n%s, time format need to be %s' % (time_str, e, '%Y-%m-%d %H:%M:%S'))


    @staticmethod
    def sub_minutes(t, delta, stdio=None):
        try:
            return (t - datetime.timedelta(minutes=delta)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            stdio.exception('%s get time fialed, error:\n%s' % (t, e))


    @staticmethod
    def add_minutes(t, delta, stdio=None):
        try:
            return (t + datetime.timedelta(minutes=delta)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            stdio.exception('%s get time fialed, error:\n%s' % (t, e))

    @staticmethod
    def parse_time_from_to(from_time=None, to_time=None, stdio=None):
        format_from_time = None
        format_to_time = None
        sucess = False
        if from_time:
            format_from_time = TimeUtils.get_format_time(from_time, stdio)
            format_to_time = TimeUtils.get_format_time(to_time, stdio) if to_time else TimeUtils.add_minutes(format_from_time, 30)
        else:
            if to_time:
                format_to_time = TimeUtils.get_format_time(to_time, stdio)
                format_from_time = TimeUtils.sub_minutes(format_to_time, 30)
        if format_from_time and format_to_time:
            sucess = True
        return format_from_time, format_to_time, sucess

    @staticmethod
    def parse_time_since(since=None, stdio=None):
        now_time = datetime.datetime.now()
        format_to_time = (now_time + datetime.timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        try:
            format_from_time = (now_time - datetime.timedelta(seconds=TimeUtils.parse_time_sec(since))).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            stdio.exception('%s parse time fialed, error:\n%s' % (since, e))
            format_from_time = TimeUtils.sub_minutes(format_to_time, 30)
        return format_from_time, format_to_time


class Cursor(SafeStdio):

    def __init__(self, ip, port, user='root', tenant='sys', password='', mode='mysql', stdio=None):
        self.stdio = stdio
        self.mode = mode
        self.ip = ip
        self.port = port
        self._user = user if mode == 'mysql' else (user if user else 'SYS') + '@' + tenant
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
        raise_cursor = copy(self)
        raise_cursor._raise_exception = True
        self._raise_cursor = raise_cursor
        return raise_cursor

    if sys.version_info.major == 2:
        def _connect(self):
            if self.mode != 'mysql':
                self.stdio.error('python2 only support mysql mode')
                return False
            self.stdio.verbose('connect %s -P%s -u%s -p%s' % (self.ip, self.port, self.user, self.password))
            self.db = mysql.connect(host=self.ip, user=self.user, port=int(self.port), passwd=str(self.password))
            self.cursor = self.db.cursor(cursorclass=mysql.cursors.DictCursor)
    else:
        def _connect(self):
            if self.mode == 'mysql':
                self.stdio.verbose('mysql connect %s -P%s -u%s -p%s' % (self.ip, self.port, self.user, self.password))
                self.db = mysql.connect(host=self.ip, user=self.user, port=int(self.port), password=str(self.password),
                                        cursorclass=mysql.cursors.DictCursor, charset='utf8mb4')
                self.cursor = self.db.cursor()
            elif self.mode == 'oracle':
                try:
                    import cx_Oracle
                    global init_cx_oracle
                    if not init_cx_oracle:
                        OBD_INSTALL_PATH = COMMAND_ENV.get(ENV.ENV_OBD_INSTALL_PATH, os.path.join(COMMAND_ENV.get(ENV.ENV_OBD_INSTALL_PRE, '/'), 'usr/obd/'))
                        cx_Oracle.init_oracle_client(os.path.join(OBD_INSTALL_PATH, 'lib/site-packages'))
                        init_cx_oracle = True
                    self.stdio.verbose(
                        'oracle connect %s -P%s -u%s -p%s' % (self.ip, self.port, self.user, self.password))
                    self.db = cx_Oracle.connect(self.user, self.password, "%s:%s" % (self.ip, self.port))
                    self.cursor = self.db.cursor()
                except Exception as e:
                    self.stdio.verbose('connect %s -P%s -u%s -p%s failed, error:\n%s' % (self.ip, self.port, self.user, self.password, e))
            else:
                self.stdio.error('only support mysql and oracle mode')
                return False

    @property
    def usable_cursor(self):
        count = 600
        self.stdio.start_loading('wait observer usable')
        while count:
            if self.execute('show databases', raise_exception=False, exc_level='verbose'):
                self.stdio.stop_loading('succeed')
                return self
            else:
                count -= 1
                time.sleep(3)
                self.close()
                self._connect()
        self.stdio.stop_loading('fail')
        raise Exception('get usable cursor failed')

    def new_cursor(self, tenant='sys', user='root', password='', ip='', port='', mode='mysql', print_exception=True):
        try:
            ip = ip if ip else self.ip
            port = port if port else self.port
            return Cursor(ip=ip, port=port, user=user, tenant=tenant, password=password, mode=mode, stdio=self.stdio)
        except:
            print_exception and self.stdio.exception('')
            self.stdio.verbose('fail to connect %s -P%s -u%s@%s  -p%s' % (ip, port, user, tenant, password))
            return None

    def execute(self, sql, args=None, execute_func=None, raise_exception=False, exc_level='error', stdio=None):
        try:
            stdio.verbose('%s execute sql: %s. args: %s' % (self.mode, sql, args))
            if not args:
                self.cursor.execute(sql)
            else:
                self.cursor.execute(sql, args)
            if not execute_func:
                return self.cursor
            return getattr(self.cursor, execute_func)()
        except Exception as e:
            getattr(stdio, exc_level)(EC_SQL_EXECUTE_FAILED.format(sql=sql))
            if raise_exception is None:
                raise_exception = self._raise_exception
            if raise_exception:
                stdio.exception('')
                raise e
            return False

    def fetchone(self, sql, args=None, raise_exception=False, exc_level='error', stdio=None):
        return self.execute(sql, args=args, execute_func='fetchone', raise_exception=raise_exception, exc_level=exc_level, stdio=stdio)

    def fetchall(self, sql, args=None, raise_exception=False, exc_level='error', stdio=None):
        return self.execute(sql, args=args, execute_func='fetchall', raise_exception=raise_exception, exc_level=exc_level, stdio=stdio)

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.db:
            self.db.close()
            self.db = None

    def reconnect(self):
        self.close()
        self._connect()


class Exector(SafeStdio):

    def __init__(self, host, port, user, pwd, exector_path, stdio):
        self._host = host
        self._port = port
        self._user = user
        self._pwd = pwd
        self._cmd = None
        self.stdio = stdio
        self._exector = os.path.join(exector_path, 'executer27/bin/executer')

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def user(self):
        return self._user

    @property
    def pwd(self):
        return self._pwd

    @property
    def exector(self):
        return self._exector

    @property
    def cmd(self):
        if self._cmd is None:
            self._cmd = '%s %%s' % self._exector
        return self._cmd

    @host.setter
    def host(self, value):
        self._host = value
        self._cmd = None

    @port.setter
    def port(self, value):
        self._port = value
        self._cmd = None

    @user.setter
    def user(self, value):
        self._user = value
        self._cmd = None

    @pwd.setter
    def pwd(self, value):
        self._pwd = value
        self._cmd = None

    @exector.setter
    def exector(self, exector_path):
        self._exector = os.path.join(exector_path, 'bin/executer27')
        self._cmd = None

    def create_temp(self, repository, direct_upgrade=False):
        tmp_path = os.path.join('/tmp', self.tmp_prefix, repository.md5)
        if not os.path.exists(tmp_path):
            relative_dir = 'etc/direct_upgrade' if direct_upgrade else 'etc'
            script_dir = os.path.join(repository.repository_dir, relative_dir)
            from ssh import LocalClient
            LocalClient.put_dir(script_dir, tmp_path)
        return tmp_path

    def clear_temp(self):
        tmp_path = os.path.join('/tmp', self.tmp_prefix)
        DirectoryUtil.rm(tmp_path)

    def exec_script(self, name, repository, can_skip=True, param=''):
        path = os.path.join(repository.repository_dir, 'bin', name)
        self.stdio.verbose('exec %s %s' % (repository, name))
        try:
            if os.path.exists(path):
                cmd = '{} {}'.format(self.cmd.replace('%s', path, 1), param)
                self.stdio.start_loading('Exec %s %s' % (repository, name))
                from ssh import LocalClient
                if LocalClient.execute_command(cmd, stdio=self.stdio):
                    self.stdio.stop_loading('succeed')
                    return True
                else:
                    self.stdio.stop_loading('fail')
                    return False
            else:
                if can_skip:
                    self.stdio.print('skip %s %s' % (repository, name))
                    return True
                else:
                    self.stdio.error('No such file: %s' % path)
                    return False
        except:
            pass


class EnvVariables(object):
    def __init__(self, environments, client):
        self.environments = environments
        self.client = client
        self.env_done = {}

    def __enter__(self):
        for env_key, env_value in self.environments.items():
            self.env_done[env_key] = self.client.get_env(env_key)
            self.client.add_env(env_key, env_value, True)

    def __exit__(self, *args, **kwargs):
        for env_key, env_value in self.env_done.items():
            if env_value is not None:
                self.client.add_env(env_key, env_value, True)
            else:
                self.client.del_env(env_key)


class GetStdio(SafeStdio):

    @classmethod
    def stdio(cls, stdio=None):
        return stdio


def get_option(options, key, default=''):
    value = getattr(options, key, default)
    if not value:
        value = default
    return value


def get_port_socket_inode(client, port, stdio=GetStdio.stdio()):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{if($4==\"0A\") print $2,$4,$10}' | grep ':%s' | awk -F' ' '{print $3}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def confirm_port(client, pid, port):
    socket_inodes = get_port_socket_inode(client, port)
    if not socket_inodes:
        return False
    ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False


def set_plugin_context_variables(plugin_context, variable_dict):
    for key, value in variable_dict.items():
        plugin_context.set_variable(key, value)


def get_disk_info(all_paths, client, stdio):
    overview_ret = True
    disk_info = get_disk_info_by_path('', client, stdio)
    if not disk_info:
        overview_ret = False
        disk_info = get_disk_info_by_path('/', client, stdio)
        if not disk_info:
            disk_info['/'] = {'total': 0, 'avail': 0, 'need': 0, 'threshold': 2}
    all_path_success = {}
    for path in all_paths:
        all_path_success[path] = False
        cur_path = path
        while cur_path not in disk_info:
            disk_info_for_current_path = get_disk_info_by_path(cur_path, client, stdio)
            if disk_info_for_current_path:
                disk_info.update(disk_info_for_current_path)
                all_path_success[path] = True
                break
            else:
                cur_path = os.path.dirname(cur_path)
    if overview_ret or all(all_path_success.values()):
        return disk_info

def get_disk_info_by_path(path, client, stdio):
    disk_info = {}
    ret = client.execute_command('df --block-size=1024 {}'.format(path))
    if ret:
        for total, used, avail, puse, path in re.findall(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(.+)', ret.stdout):
            disk_info[path] = {'total': int(total) << 10, 'avail': int(avail) << 10, 'need': 0, 'threshold': 2}
            stdio.verbose('get disk info for path {}, total: {} avail: {}'.format(path, disk_info[path]['total'], disk_info[path]['avail']))
    return disk_info


def str2bool(value):
    if value.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ValueError('{} is not a valid boolean value'.format(value))

def is_root_user(client):
    return client.config.username == 'root'


def string_to_md5_32bytes(input_str):
    md5_hash = hashlib.md5()
    md5_hash.update(input_str.encode('utf-8'))
    return md5_hash.hexdigest()


def aes_encrypt(plaintext, key):
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + ciphertext).decode('utf-8')


def aes_decrypt(ciphertext, key):
    raw_data = base64.b64decode(ciphertext)
    iv = raw_data[:AES.block_size]
    ciphertext = raw_data[AES.block_size:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext.decode('utf-8')


def get_system_memory(memory_limit):
    if memory_limit < 12 << 30:
        system_memory = 1 << 30
    elif memory_limit < 20 << 30:
        system_memory = 5 << 30
    elif memory_limit < 40 << 30:
        system_memory = 6 << 30
    elif memory_limit < 60 << 30:
        system_memory = 7 << 30
    elif memory_limit < 80 << 30:
        system_memory = 8 << 30
    elif memory_limit < 100 << 30:
        system_memory = 9 << 30
    elif memory_limit < 130 << 30:
        system_memory = 10 << 30
    else:
        system_memory = int(memory_limit * 0.08)
    return system_memory


def get_sys_cpu(cpu_count):
    if cpu_count < 8:
        sys_cpu = 1
    elif cpu_count < 16:
        sys_cpu = 2
    elif cpu_count < 32:
        sys_cpu = 3
    else:
        sys_cpu = 4
    return sys_cpu

def get_sys_log_disk_size(memory_limit):
    if memory_limit < 12 << 30:
        sys_log_disk_size = 2 << 30
    elif memory_limit < 40 << 30:
        sys_log_disk_size = 3 << 30
    elif memory_limit < 80 << 30:
        sys_log_disk_size = 4 << 30
    elif memory_limit < 128 << 30:
        sys_log_disk_size = 5 << 30
    else:
        sys_log_disk_size = int(memory_limit * 0.03) + (1 << 30)
    return sys_log_disk_size

def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', print_exception=True, retries=20, args=[], stdio=None):
    if not user:
        user = 'SYS' if mode == 'oracle' else 'root'
    # find tenant ip, port
    tenant_cursor = None
    query_sql = "select a.SVR_IP,c.SQL_PORT from oceanbase.DBA_OB_UNITS as a, oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME=%s"
    tenant_server_ports = cursor.fetchall(query_sql, (tenant, ), raise_exception=False, exc_level='verbose')
    for tenant_server_port in tenant_server_ports:
        tenant_ip = tenant_server_port['SVR_IP']
        tenant_port = tenant_server_port['SQL_PORT']
        tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password if retries % 2 or not len(args) > 0 else args[0], ip=tenant_ip, port=tenant_port, print_exception=False)
        if tenant_cursor:
            break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, print_exception=print_exception, retries=retries-1, args=args, stdio=stdio)
    return tenant_cursor.execute(sql, args=args, raise_exception=False, exc_level='verbose', stdio=stdio) if tenant_cursor else False


def port_check(port, client, ports, stdio):
    if get_port_socket_inode(client, port):
        stdio.print(FormatText.error(f'The port {port} is already in use. Please enter a different port.'))
        return False, ports
    if port in ports:
        stdio.print(FormatText.error(f'The port {port} has already been specified above.'))
        return False, ports
    else:
        ports.append(port)
        return True, ports


def is_all_digits(input_str, stdio):
    DIGIT_PATTERN = re.compile(r'^\d+$')
    if not bool(DIGIT_PATTERN.fullmatch(str(input_str))):
        stdio.error(f"Invalid input: {input_str}. Only digits are allowed. Please try again.")
        return False
    return True


def input_int_value(name, min_value, max_value, unit='G', default_value=None, stdio=None):
    if unit and unit not in ["B", "K", "M", "G", "T", "P"]:
        stdio.error(f"Invalid unit: {unit}.")
        return False
    if int(min_value) > int(max_value):
        stdio.error(f"{name}: min_value cannot exceed max_value.")
        return False
    default_value = default_value or min_value
    while True:
        input_value = stdio.read(f'Enter the {name} (Configurable Range[{min_value}, {max_value}], Default: {default_value} {f", unit: {unit}" if unit else ""}): ', blocked=True).strip() or default_value
        if not is_all_digits(input_value, stdio):
            continue
        if int(input_value) < int(min_value):
            stdio.print(FormatText.error(f"Cannot be less than the min_value ({min_value}). Please try again."))
            continue
        if int(input_value) > int(max_value):
            stdio.print(FormatText.error(f"Cannot exceed the max_value ({max_value}). Please try again."))
            continue
        break
    return input_value


def byte_to_GB(byte):
    aa = int(byte // (1024 * 1024 * 1024))
    return int(byte // (1024 * 1024 * 1024))


def set_system_conf(client, ip, var, value, stdio, var_type='ulimits', username=None):
    sudo_prefix = get_sudo_prefix(client)
    if var_type == 'ulimits':
        if not client.execute_command('echo -e "{username} soft {name} {value}\\n{username} hard {name} {value}" | {sudo_prefix}tee -a /etc/security/limits.d/{name}.conf'.format(username=username or client.config.username, name=var, value=value, sudo_prefix=sudo_prefix)):
            return False
    else:
        ret = client.execute_command('echo "{0}={1}" | {2}tee -a /etc/sysctl.conf; sudo sysctl -p'.format(var, value, sudo_prefix))
        if not ret:
            if ret.stdout and "%s = %s" % (var, value) == ret.stdout.strip().split('\n')[-1]:
                return True
            else:
                stdio.error(_errno.WC_CHANGE_SYSTEM_PARAMETER_FAILED.format(server=ip, key=var))
                return False
    return True


def get_sudo_prefix(client):
    prefix = 'sudo '
    if client.config.username == 'root':
        prefix = ''
    return prefix

def contains_duplicate_nodes(servers):
    ips = [server.ip for server in servers]
    ip_counter = Counter(ips)
    duplicates = {ip: count for ip, count in ip_counter.items() if count > 1}
    return duplicates


def get_tenant_connect_host_port(tenant_name, cursor):
    query_sql = 'select a.SVR_IP,c.SQL_PORT from oceanbase.DBA_OB_UNITS as a, oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME="%s"'
    tenant_server_ports = cursor.fetchall(query_sql % tenant_name, raise_exception=False, exc_level='verbose')
    for tenant_server_port in tenant_server_ports:
        return tenant_server_port['SVR_IP'], tenant_server_port['SQL_PORT']


def get_metadb_info_from_depends_ob(cluster_config, stdio=None):
    def get_jdbc_ip_and_port():
        ret = {}
        if (obproxy_server_config.get('vip_address') and obproxy_server_config.get('vip_port')) or obproxy_server_config.get('dns'):
            if obproxy_server_config.get('dns'):
                ret = {'ip': obproxy_server_config['dns'], 'port': obproxy_server_config['listen_port']}
                stdio.verbose("get obproxy dns: {}".format(obproxy_server_config['dns']))
            elif obproxy_server_config.get('vip_address') and obproxy_server_config.get('vip_port'):
                ret = {'ip': obproxy_server_config['vip_address'], 'port': obproxy_server_config['vip_port']}
                stdio.verbose("get obproxy vip: {} ".format(obproxy_server_config['vip_address'] + ":" + str(obproxy_server_config['vip_port'])))
        else:
            ret = {"ip": obproxy_server.ip, "port": obproxy_server_config['listen_port']}
        return ret
    meta_db_info = {}
    for comp in const.COMPS_ODP:
        if comp in cluster_config.depends:
            obproxy_servers = cluster_config.get_depend_servers(comp)
            obproxy_server = obproxy_servers[0]
            obproxy_server_config = cluster_config.get_depend_config(comp, obproxy_server)
            ip_ret = get_jdbc_ip_and_port()
            if ip_ret:
                meta_db_info['host'] = ip_ret['ip']
                meta_db_info['port'] = ip_ret['port']
                meta_db_info['user'] = 'root'
                meta_db_info['password'] = obproxy_server_config['observer_root_password']
    if not meta_db_info:
        for ob_comp in const.COMPS_OB:
            if ob_comp in cluster_config.depends:
                ob_servers = cluster_config.get_depend_servers(ob_comp)
                for ob_server in ob_servers:
                    ob_server_conf = cluster_config.get_depend_config(ob_comp, ob_server)
                    meta_db_info['user'] = 'root'
                    meta_db_info['password'] = ob_server_conf['root_password']
                    cursor = Cursor(ob_server.ip, ob_server_conf['mysql_port'], user='root', password=ob_server_conf['root_password'], stdio=stdio)
                    host, port = get_tenant_connect_host_port('sys', cursor)
                    meta_db_info['host'] = host
                    meta_db_info['port'] = port
                    return meta_db_info
    return meta_db_info



def docker_run_sudo_prefix(client):
    if not client.execute_command('docker images'):
        prefix = 'sudo '
    else:
        prefix = ''
    return prefix

def docker_compose_run_sudo_prefix(client):
    if not client.execute_command('docker compose ls >/dev/null 2>&1'):
        prefix = 'sudo '
    else:
        prefix = ''
    return prefix


def add_http_prefix(url):
    if url and url.startswith('http://') or url.startswith('https://'):
        return url
    else:
        return 'http://' + url