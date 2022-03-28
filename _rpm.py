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
import re
import sys

import rpmfile
# py3和py2 的 lzma 模块不同
# python3 标准库中有 lzma 
# python2下没有lzma这个三方库，而是使用动态库。pip 提供了pyliblzma这个三方库，这个也是动态库。与centos python自带的是一样的
# python2的lzma的api与py3 的不同
# python2 三方库中backports.lzma的api与python3的相同
# 但rpmfile中 只会尝试 import lzma。这在python2下 只能
# 故这里先import rpmfile, 在为rpmfile 注入 正确的 lzma依赖
if sys.version_info.major == 2:
    from backports import lzma
    setattr(sys.modules['rpmfile'], 'lzma', getattr(sys.modules[__name__], 'lzma'))


class Version(str):

    def __init__(self, bytes_or_buffer, encoding=None, errors=None):
        super(Version, self).__init__()

    @property
    def __cmp_value__(self):
        return [(int(_i), _s) for _i, _s in re.findall('(\d+)([^\.]*)', self.__str__())]

    def __eq__(self, value):
        if value is None:
            return False
        return self.__cmp_value__ == self.__class__(value).__cmp_value__

    def __gt__(self, value):
        if value is None:
            return True
        return self.__cmp_value__ > self.__class__(value).__cmp_value__

    def __ge__(self, value):
        if value is None:
            return True
        return self.__eq__(value) or self.__gt__(value)

    def __lt__(self, value):
        if value is None:
            return False
        return self.__cmp_value__ < self.__class__(value).__cmp_value__

    def __le__(self, value):
        if value is None:
            return False
        return self.__eq__(value) or self.__lt__(value)

class Release(Version):

    @property
    def __cmp_value__(self):
        m = re.search('(\d+)', self.__str__())
        return int(m.group(0)) if m else -1


class PackageInfo(object):

    def __init__(self, name, version, release, arch, md5):
        self.name = name
        self.set_version(version)
        self.set_release(release)
        self.arch = arch
        self.md5 = md5

    def set_version(self, version):
        self.version = Version(str(version) if version else '')

    def set_release(self, release):
        self.release = Release(str(release) if release else '')

    def __str__(self):
        return 'name: %s\nversion: %s\nrelease:%s\narch: %s\nmd5: %s' % (self.name, self.version, self.release, self.arch, self.md5)

    @property
    def __cmp_value__(self):
        return [self.version, self.release]

    def __hash__(self):
        return hash(self.md5)

    def __eq__(self, value):
        if value is None:
            return False
        return self.md5 == value.md5

    def __ne__(self, value):
        return not self.__eq__(value)

    def __gt__(self, value):
        return value is None or self.__cmp_value__ > value.__cmp_value__
    
    def __ge__(self, value):
        return value is None or self.__eq__(value) or self.__cmp_value__ >= value.__cmp_value__

    def __lt__(self, value):
        if value is None:
            return False
        return self.__cmp_value__ < value.__cmp_value__

    def __le__(self, value):
        if value is None:
            return False
        return self.__eq__(value) or self.__cmp_value__ <= value.__cmp_value__


class Package(PackageInfo):

    def __init__(self, path):
        self.path = path
        with self.open() as rpm:
            super(Package, self).__init__(
                name = rpm.headers.get('name').decode(),
                version = rpm.headers.get('version').decode(),
                release = rpm.headers.get('release').decode(),
                arch = rpm.headers.get('arch').decode(),
                md5 = rpm.headers.get('md5').decode()
            )

    def __str__(self):
        return 'name: %s\nversion: %s\nrelease:%s\narch: %s\nmd5: %s' % (self.name, self.version, self.release, self.arch, self.md5)

    def __hash__(self):
        return hash(self.path)

    @property
    def file_name(self):
        return '%s-%s-%s.%s.rpm' % (self.name, self.version, self.release, self.arch)

    def open(self):
        return rpmfile.open(self.path)
    
