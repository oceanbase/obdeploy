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


class Package(object):

    def __init__(self, path):
        self.path = path
        with self.open() as rpm:
            self.name = rpm.headers.get('name').decode()
            self.version = rpm.headers.get('version').decode()
            self.release = rpm.headers.get('release').decode()
            self.arch = rpm.headers.get('arch').decode()
            self.md5 = rpm.headers.get('md5').decode()

    def __str__(self):
        return 'name: %s\nversion: %s\nrelease:%s\narch: %s\nmd5: %s' % (self.name, self.version, self.release, self.arch, self.md5)

    @property
    def file_name(self):
        return '%s-%s-%s.%s.rpm' % (self.name, self.version, self.release, self.arch)

    def open(self):
        return rpmfile.open(self.path)
    
