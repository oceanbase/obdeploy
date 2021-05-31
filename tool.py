
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
import sys
import stat
import gzip
import shutil

from ruamel.yaml import YAML

if sys.version_info.major == 2:
    from backports import lzma
else:
    import lzma


_WINDOWS = os.name == 'nt'


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
            return transform_func(value) if transform_func else value
        except:
            return default


class DirectoryUtil(object):

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
                FileUtil.copy(src_name, dst_name)
        for link_dest, dst_name in links:
            DirectoryUtil.rm(dst_name, stdio)
            os.symlink(link_dest, dst_name)
        return ret

    @staticmethod
    def mkdir(path, mode=0o755, stdio=None):
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
        try:
            if os.path.exists(path):
                if os.path.islink(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
            return True
        except Exception as e:
            stdio and getattr(stdio, 'exception', print)('')
            stdio and getattr(stdio, 'error', print)('failed to remove %s', path)
        return False


class FileUtil(object):

    COPY_BUFSIZE = 1024 * 1024 if _WINDOWS else 64 * 1024

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
                os.symlink(os.readlink(src), dst)
                return True
            with FileUtil.open(src, 'rb') as fsrc:
                with FileUtil.open(dst, 'wb') as fdst:
                    FileUtil.copy_fileobj(fsrc, fdst)
                    return True
        except Exception as e:
            if stdio:
                getattr(stdio, 'exception', print)('copy error')
            else:
                raise e
        return False

    @staticmethod
    def open(path, _type='r', stdio=None):
        if os.path.exists(path):
            if os.path.isfile(path):
                return open(path, _type)
            info = '%s is not file' % path
            if stdio:
                getattr(stdio, 'error', print)(info)
                return None
            else:
                raise IOError(info)
        dir_path, file_name = os.path.split(path)
        if not dir_path or DirectoryUtil.mkdir(dir_path, stdio=stdio):
            return open(path, _type)
        info = '%s is not file' % path
        if stdio:
            getattr(stdio, 'error', print)(info)
            return None
        else:
            raise IOError(info)

    @staticmethod
    def unzip(source, ztype=None, stdio=None):
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
                s_fn = open(unzip, 'r')
            return s_fn
        except:
            stdio and getattr(stdio, 'exception', print)('failed to unzip %s' % source)
        return None

    @staticmethod
    def rm(path, stdio=None):
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


class YamlLoader(YAML):

    def __init__(self, stdio=None, typ=None, pure=False, output=None, plug_ins=None):
        super(YamlLoader, self).__init__(typ=typ, pure=pure, output=output, plug_ins=plug_ins)
        self.stdio = stdio
    
    def load(self, stream):
        try:
            return super(YamlLoader, self).load(stream)
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
