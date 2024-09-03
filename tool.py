
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
import hashlib
import socket
import datetime
from io import BytesIO
from copy import copy

import string
from ruamel.yaml import YAML, YAMLContextManager, representer

from _errno import EC_SQL_EXECUTE_FAILED
from _stdio import SafeStdio

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
            yaml_content = str(yaml_content).encode()
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
        raise_cursor = copy(self)
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
            self.stdio.verbose('fail to connect %s -P%s -u%s@%s  -p%s' % (ip, port, user, tenant, password))
            return None

    def execute(self, sql, args=None, execute_func=None, raise_exception=False, exc_level='error', stdio=None):
        try:
            stdio.verbose('execute sql: %s. args: %s' % (sql, args))
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
