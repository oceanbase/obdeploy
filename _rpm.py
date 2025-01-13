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

import hashlib
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
        return [(int(_i), _s) for _i, _s in re.findall('(\d+)([^\._]*)', self.__str__())]

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

    def simple(self):
        m = re.search('(\d+)', self.__str__())
        return m.group(0) if m else ""

class PackageInfo(object):

    def __init__(self, name, version, release, arch, md5, size):
        self.name = name
        self.set_version(version)
        self.set_release(release)
        self.arch = arch
        self.md5 = md5
        self.size = size

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
                md5 = rpm.headers.get('md5').decode(),
                size = rpm.headers.get('size')
            )

    def __str__(self):
        return 'name: %s\nversion: %s\nrelease:%s\narch: %s\nmd5: %s\nsize: %s' % (self.name, self.version, self.release, self.arch, self.md5, self.size)

    def __hash__(self):
        return hash(self.path)

    @property
    def file_name(self):
        return '%s-%s-%s.%s.rpm' % (self.name, self.version, self.release, self.arch)

    def open(self):
        return rpmfile.open(self.path)



def get_version_from_array(array):
        version = ''
        for _i, _s in array:
            version=version + str(_i) + _s
        return Version(version)
    
def add_sub_version(version, offset=1, add=1):
    """
    add the version by offset and add value

    :param version: version
    :param offset: the offset number of the version
    :param add: the add value
    :return: the new version after adding
    """
    version_array = version.__cmp_value__
    version_array[offset-1] = (version_array[offset-1][0] + add, version_array[offset-1][1])
    return get_version_from_array(version_array)

def get_prefix_version(version, offset=0):
    """
    get prefix sub version

    :param version: version
    :param offset: the offset number of the version
    :return: the new version after geting prefix
    """
    if not offset:
        return version
    if offset >= len(version.__cmp_value__):
        return version
    version_array = version.__cmp_value__[:offset]
    return get_version_from_array(version_array)[:-1]
    
