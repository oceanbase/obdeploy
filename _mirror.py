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


import re
import os
import sys
import time
import pickle
import string
import requests
from glob import glob
from enum import Enum
from copy import deepcopy
from xml.etree import cElementTree
try:
    from ConfigParser import ConfigParser
except:
    from configparser import ConfigParser

from _arch import getArchList, getBaseArch
from _rpm import Package, PackageInfo
from tool import ConfigUtil, FileUtil
from _manager import Manager


_KEYCRE = re.compile(r"\$(\w+)")
_ARCH = getArchList()
_RELEASE = None
SUP_MAP = {
    'ubuntu': (([16], 7), ),
    'debian': (([9], 7), ),
    'opensuse-leap': (([15], 7), ),
    'sles': (([15, 2], 7), ),
    'fedora': (([33], 7), ),
    'uos': (([20], 8), ),
}
_SERVER_VARS = {
    'basearch': getBaseArch(),
}
with FileUtil.open('/etc/os-release') as f:
    for line in f.readlines():
        line = line.strip()
        if not line:
            continue
        try:
            k, v = line.split('=', 1)
            _SERVER_VARS[k] = v.strip('"').strip("'")
        except:
            pass
    if 'VERSION_ID' in _SERVER_VARS:
        m = re.match('\d+', _SERVER_VARS['VERSION_ID'])
        if m:
            _RELEASE = m.group(0)
_SERVER_VARS['releasever'] = _RELEASE



class MirrorRepositoryType(Enum):

    LOCAL = 'local'
    REMOTE = 'remote'


class MirrorRepository(object):
    
    MIRROR_TYPE = None

    def __init__(self, mirror_path, stdio=None):
        self.stdio = stdio
        self.mirror_path = mirror_path
        self.name = os.path.split(mirror_path)[1]
        self._str = '%s mirror %s' % (self.mirror_type, self.name)

    def __str__(self):
        return self._str

    @property
    def mirror_type(self):
        return self.MIRROR_TYPE

    
    def get_all_pkg_info(self):
        return []

    def get_best_pkg(self, **pattern):
        info = self.get_best_pkg_info(**pattern)
        return self.get_rpm_pkg_by_info(info) if info else None

    def get_exact_pkg(self, **pattern):
        info = self.get_exact_pkg_info(**pattern)
        return self.get_rpm_pkg_by_info(info) if info else None

    def get_rpm_pkg_by_info(self, pkg_info):
        return None
    
    def get_pkgs_info(self, **pattern):
        return []

    def get_best_pkg_info(self, **pattern):
        return None

    def get_exact_pkg_info(self, **pattern):
        return None

    def get_pkgs_info_with_score(self, **pattern):
        return []


class RemoteMirrorRepository(MirrorRepository):
    class RemotePackageInfo(PackageInfo):

        def __init__(self, elem):
            self.epoch = None
            self.location = (None, None)
            self.checksum = (None,None) # type,value
            self.openchecksum = (None,None) # type,value
            self.time = (None, None)
            super(RemoteMirrorRepository.RemotePackageInfo, self).__init__(None, None, None, None, None)
            self._parser(elem)

        @property
        def md5(self):
            return self.checksum[1]

        @md5.setter
        def md5(self, value):
            self.checksum = (self.checksum[0], value)

        def __str__(self):
            url = self.location[1]
            if self.location[0]:
                url = self.location[0] + url
            return url

        def _parser(self, elem):
            tags = self.__dict__.keys()
            for child in elem:
                child_name = RemoteMirrorRepository.ns_cleanup(child.tag)
                if child_name == 'location':
                    relative = child.attrib.get('href')
                    base = child.attrib.get('base')
                    self.location = (base, relative)
                    
                elif child_name == 'checksum':
                    csum_value = child.text
                    csum_type = child.attrib.get('type')
                    self.checksum = (csum_type,csum_value)

                elif child_name == 'open-checksum':
                    csum_value = child.text
                    csum_type = child.attrib.get('type')
                    self.openchecksum = (csum_type, csum_value)

                elif child_name == 'version':
                    self.epoch = child.attrib.get('epoch')
                    self.set_version(child.attrib.get('ver'))
                    self.set_release(child.attrib.get('rel'))

                elif child_name == 'time':
                    build = child.attrib.get('build')
                    _file = child.attrib.get('file')
                    self.time = (int(_file), int(build))
                    
                elif child_name == 'arch':
                    self.arch = child.text
                elif child_name == 'name':
                    self.name = child.text

    class RepoData(object):

        def __init__(self, elem):
            self.type = None
            self.type = elem.attrib.get('type')
            self.location = (None, None)
            self.checksum = (None,None) # type,value
            self.openchecksum = (None,None) # type,value
            self.timestamp = None
            self.dbversion = None
            self.size      = None
            self.opensize  = None
            self.deltas    = []
            self._parser(elem)
        
        def _parser(self, elem):
            for child in elem:
                child_name = RemoteMirrorRepository.ns_cleanup(child.tag)
                if child_name == 'location':
                    relative = child.attrib.get('href')
                    base = child.attrib.get('base')
                    self.location = (base, relative)
                
                elif child_name == 'checksum':
                    csum_value = child.text
                    csum_type = child.attrib.get('type')
                    self.checksum = (csum_type,csum_value)

                elif child_name == 'open-checksum':
                    csum_value = child.text
                    csum_type = child.attrib.get('type')
                    self.openchecksum = (csum_type, csum_value)
                
                elif child_name == 'timestamp':
                    self.timestamp = child.text
                elif child_name == 'database_version':
                    self.dbversion = child.text
                elif child_name == 'size':
                    self.size = child.text
                elif child_name == 'open-size':
                    self.opensize = child.text
                elif child_name == 'delta':
                    delta = RepoData(child)
                    delta.type = self.type
                    self.deltas.append(delta)

    MIRROR_TYPE = MirrorRepositoryType.REMOTE
    REMOTE_REPOMD_FILE = '/repodata/repomd.xml'
    REPOMD_FILE = 'repomd.xml'
    OTHER_DB_FILE = 'other_db.xml'
    REPO_AGE_FILE = '.rege_age'
    PRIMARY_REPOMD_TYPE = 'primary'

    def __init__(self, mirror_path, meta_data, stdio=None):
        self.baseurl = None
        self.repomd_age = 0
        self.repo_age = 0
        self.priority = 1
        self.gpgcheck = False
        self._db = None
        self._repomds = None
        super(RemoteMirrorRepository, self).__init__(mirror_path, stdio=stdio)
        self.baseurl = meta_data['baseurl']
        self.gpgcheck = ConfigUtil.get_value_from_dict(meta_data, 'gpgcheck', 0, int) > 0
        self.priority = 100 - ConfigUtil.get_value_from_dict(meta_data, 'priority', 99, int)
        if os.path.exists(mirror_path):
            self._load_repo_age()
        repo_age = ConfigUtil.get_value_from_dict(meta_data, 'repo_age', 0, int)
        if repo_age > self.repo_age or int(time.time()) - 86400 > self.repo_age:
            self.repo_age = repo_age
            self.update_mirror()

    @property
    def db(self):
        if self._db is not None:
            return self._db
        primary_repomd = self._get_repomd_by_type(self.PRIMARY_REPOMD_TYPE)
        if not primary_repomd:
            return []
        file_path = self._get_repomd_data_file(primary_repomd)
        if not file_path:
            return []
        fp = FileUtil.unzip(file_path)
        if not fp:
            return []
        self._db = {}
        parser = cElementTree.iterparse(fp)
        for event, elem in parser:
            if RemoteMirrorRepository.ns_cleanup(elem.tag) == 'package' and elem.attrib.get('type') == 'rpm':
                info = RemoteMirrorRepository.RemotePackageInfo(elem)
                # self._db.append(info)
                self._db[info.md5] = info
        return self._db

    @staticmethod
    def ns_cleanup(qn):
        return qn if qn.find('}') == -1 else qn.split('}')[1]

    @staticmethod
    def get_repo_age_file(mirror_path):
        return os.path.join(mirror_path, RemoteMirrorRepository.REPO_AGE_FILE)

    @staticmethod
    def get_repomd_file(mirror_path):
        return os.path.join(mirror_path, RemoteMirrorRepository.REPOMD_FILE)

    @staticmethod
    def get_other_db_file(mirror_path):
        return os.path.join(mirror_path, RemoteMirrorRepository.OTHER_DB_FILE)

    @staticmethod
    def var_replace(string, var):
        if not var:
            return string
        done = []                      

        while string:
            m = _KEYCRE.search(string)
            if not m:
                done.append(string)
                break

            varname = m.group(1).lower()
            replacement = var.get(varname, m.group())

            start, end = m.span()
            done.append(string[:start])    
            done.append(replacement)   
            string = string[end:]            

        return ''.join(done)
        

    def _load_repo_age(self):
        try:
            with open(self.get_repo_age_file(self.mirror_path), 'r') as f:
                self.repo_age = int(f.read())
        except:
            pass
    
    def _dump_repo_age_data(self):
        try:
            with open(self.get_repo_age_file(self.mirror_path), 'w') as f:
                f.write(str(self.repo_age))
            return True
        except:
            pass
        return False

    def _get_repomd_by_type(self, repomd_type):
        repodmds = self.get_repomds()
        for repodmd in repodmds:
            if repodmd.type == repomd_type:
                return repodmd

    def _get_repomd_data_file(self, repomd):
        file_name = repomd.location[1]
        repomd_name = file_name.split('-')[-1]
        file_path = os.path.join(self.mirror_path, file_name)
        if os.path.exists(file_path):
            return file_path
        base_url = repomd.location[0] if repomd.location[0] else self.baseurl
        url = '%s/%s' % (base_url, repomd.location[1])
        if self.download_file(url, file_path, self.stdio):
            return file_path

    def update_mirror(self):
        self.stdio and getattr(self.stdio, 'start_loading')('Update %s' % self.name)
        self.get_repomds(True)
        primary_repomd = self._get_repomd_by_type(self.PRIMARY_REPOMD_TYPE)
        if not primary_repomd:
            self.stdio and getattr(self.stdio, 'stop_loading')('fail')
            return False
        file_path = self._get_repomd_data_file(primary_repomd)
        if not file_path:
            self.stdio and getattr(self.stdio, 'stop_loading')('fail')
            return False
        self._db = None
        self.repo_age = int(time.time())
        self._dump_repo_age_data()
        self.stdio and getattr(self.stdio, 'stop_loading')('succeed')
        return True

    def get_repomds(self, update=False):
        path = self.get_repomd_file(self.mirror_path)
        if update or not os.path.exists(path):
            url = '%s/%s' % (self.baseurl, self.REMOTE_REPOMD_FILE)
            self.download_file(url, path, self.stdio)
            self._repomds = None
        if self._repomds is None:
            self._repomds = []
            try:
                parser = cElementTree.iterparse(path)
                for event, elem in parser:
                    if RemoteMirrorRepository.ns_cleanup(elem.tag) == 'data':
                        repod =  RemoteMirrorRepository.RepoData(elem)
                        self._repomds.append(repod)
            except:
                pass
        return self._repomds

    def get_all_pkg_info(self):
        return [self.db[key] for key in self.db]

    def get_rpm_pkg_by_info(self, pkg_info):
        file_name = pkg_info.location[1]
        file_path = os.path.join(self.mirror_path, file_name)
        self.stdio and getattr(self.stdio, 'verbose', print)('get RPM package by %s' % pkg_info)
        if not os.path.exists(file_path) or os.stat(file_path)[8] < pkg_info.time[1]:
            base_url = pkg_info.location[0] if pkg_info.location[0] else self.baseurl
            url = '%s/%s' % (base_url, pkg_info.location[1])
            if not self.download_file(url, file_path, self.stdio):
                return None
        return Package(file_path)
    
    def get_pkgs_info(self, **pattern):
        matchs = self.get_pkgs_info_with_score(**pattern)
        if matchs:
            return [info for info in sorted(matchs, key=lambda x: x[1], reverse=True)]
        return matchs

    def get_best_pkg_info(self, **pattern):
        matchs = self.get_pkgs_info_with_score(**pattern)
        if matchs:
            return Package(max(matchs, key=lambda x: x[1])[0].path)
        return None

    def get_exact_pkg_info(self, **pattern):
        if 'md5' in pattern and pattern['md5']:
            self.stdio and getattr(self.stdio, 'verbose', print)('md5 is %s' % pattern['md5'])
            return self.db[pattern['md5']] if pattern['md5'] in self.db else None
        self.stdio and getattr(self.stdio, 'verbose', print)('md5 is None')
        if 'name' not in pattern and not pattern['name']:
            self.stdio and getattr(self.stdio, 'verbose', print)('name is None')
            return None
        name = pattern['name']
        self.stdio and getattr(self.stdio, 'verbose', print)('name is %s' % name)
        arch = getArchList(pattern['arch']) if 'arch' in pattern and pattern['arch'] else _ARCH
        self.stdio and getattr(self.stdio, 'verbose', print)('arch is %s' % arch)
        release = pattern['release'] if 'release' in pattern else None
        self.stdio and getattr(self.stdio, 'verbose', print)('release is %s' % release)
        version = pattern['version'] if 'version' in pattern else None
        self.stdio and getattr(self.stdio, 'verbose', print)('version is %s' % version)
        pkgs = []
        for key in self.db:
            info = self.db[key]
            if info.name != name:
                continue
            if info.arch not in arch:
                continue
            if release and info.release != release:
                continue
            if version and version != info.version:
                continue
            pkgs.append(info)
        if pkgs:
            pkgs.sort()
            return pkgs[-1]
        else:
            return None

    def get_pkgs_info_with_score(self, **pattern):
        matchs = []
        if 'md5' in pattern and pattern['md5']:
            self.stdio and getattr(self.stdio, 'verbose', print)('md5 is %s' % pattern['md5'])
            return [self.db[pattern['md5']], (0xfffffffff, )] if pattern['md5'] in self.db else matchs
        self.stdio and getattr(self.stdio, 'verbose', print)('md5 is None')
        if 'name' not in pattern and not pattern['name']:
            self.stdio and getattr(self.stdio, 'verbose', print)('name is None')
            return matchs
        self.stdio and getattr(self.stdio, 'verbose', print)('name is %s' % pattern['name'])
        if 'arch' in pattern and pattern['arch']:
            pattern['arch'] = getArchList(pattern['arch'])
        else:
            pattern['arch'] = _ARCH
        self.stdio and getattr(self.stdio, 'verbose', print)('arch is %s' % pattern['arch'])
        if 'version' in pattern and pattern['version']:
            pattern['version'] += '.'
        else:
            pattern['version'] = None
        self.stdio and getattr(self.stdio, 'verbose', print)('version is %s' % pattern['version'])
        for key in self.db:
            info = self.db[key]
            if pattern['name'] in info.name:
                matchs.append([info, self.match_score(info, **pattern)])
        return matchs

    def match_score(self, info, name, arch, version=None):
        if info.arch not in arch:
            return [0, ]
        info_version = '%s.' % info.version
        if version and info_version.find(version) != 0:
            return [0 ,]
            
        c = [len(name) / len(info.name), info]
        return c

    @staticmethod
    def validate_repoid(repoid):
        """Return the first invalid char found in the repoid, or None."""
        allowed_chars = string.ascii_letters + string.digits + '-_.:'
        for char in repoid:
            if char not in allowed_chars:
                return char
        else:
            return None

    @staticmethod
    def download_file(url, save_path, stdio=None):
        try:
            with requests.get(url, stream=True) as fget:
                file_size = int(fget.headers["Content-Length"])
                if stdio:
                    print_bar = True
                    for func in ['start_progressbar', 'update_progressbar', 'finish_progressbar']:
                        if getattr(stdio, func, False) is False:
                            print_bar = False
                            break
                else:
                    print_bar = False
                if print_bar:
                    _, fine_name = os.path.split(save_path)
                    units = {"B": 1, "K": 1<<10, "M": 1<<20, "G": 1<<30, "T": 1<<40}
                    for unit in units:
                        num = file_size / units[unit]
                        if num < 1024:
                            break
                    stdio.start_progressbar('Download %s (%.2f %s)' % (fine_name, num, unit), file_size)
                chunk_size = 512
                file_done = 0
                with FileUtil.open(save_path, "wb", stdio) as fw:
                    for chunk in fget.iter_content(chunk_size):
                        fw.write(chunk)
                        file_done = file_done + chunk_size
                        if print_bar and file_done <= file_size:
                            stdio.update_progressbar(file_done)
                    print_bar and stdio.finish_progressbar()
            return True
        except:
            FileUtil.rm(save_path)
            stdio and getattr(stdio, 'exception', print)('Failed to download %s to %s' % (url, save_path))
        return False

class LocalMirrorRepository(MirrorRepository):

    MIRROR_TYPE = MirrorRepositoryType.LOCAL
    _DB_FILE = '.db'

    def __init__(self, mirror_path, stdio=None):
        super(LocalMirrorRepository, self).__init__(mirror_path, stdio=stdio)
        self.db = {}
        self.db_path = os.path.join(mirror_path, self._DB_FILE)
        self._load_db()

    @property
    def repo_age(self):
        return int(time.time())

    def _load_db(self):
        try:
            with open(self.db_path, 'rb') as f:
                db = pickle.load(f)
                for key in db:
                    data = db[key]
                    path = getattr(data, 'path', False)
                    if not path or not os.path.exists(path):
                        continue
                    self.db[key] = data
        except:
            self.stdio.exception('')
            pass

    def _dump_db(self):
        # 所有 dump方案都为临时
        try:
            with open(self.db_path, 'wb') as f:
                pickle.dump(self.db, f)
            return True
        except:
            self.stdio.exception('')
            pass
        return False

    def exist_pkg(self, pkg):
        return pkg.md5 in self.db

    def add_pkg(self, pkg):
        target_path = os.path.join(self.mirror_path, pkg.file_name)
        try:
            src_path = pkg.path
            self.stdio and getattr(self.stdio, 'verbose', print)('RPM hash check')
            if target_path != src_path:
                if pkg.md5 in self.db:
                    t_info = self.db[pkg.md5]
                    self.stdio and getattr(self.stdio, 'verbose', print)('copy %s to %s' % (src_path, target_path))
                    if t_info.path == target_path:
                        del self.db[t_info.md5]
                        FileUtil.copy(src_path, target_path)
                    else:
                        FileUtil.copy(src_path, target_path)
                        try:
                            self.stdio and getattr(self.stdio, 'verbose', print)('remove %s' % t_info.path)
                            os.remove(t_info.path)
                        except:
                            pass
                else:
                    FileUtil.copy(src_path, target_path)
                pkg.path = target_path
            else:
                self.stdio and getattr(self.stdio, 'error', print)('same file')
                return None
            self.db[pkg.md5] = pkg
            self.stdio and getattr(self.stdio, 'verbose', print)('dump PackageInfo')
            if self._dump_db():
                self.stdio and getattr(self.stdio, 'print', print)('add %s to local mirror', src_path)
                return pkg
        except IOError:
            self.self.stdio and getattr(self.self.stdio, 'exception', print)('')
            self.stdio and getattr(self.stdio, 'error', print)('Set local mirror failed. %s IO Error' % pkg.file_name)
        except:
            self.stdio and getattr(self.stdio, 'exception', print)('')
            self.stdio and getattr(self.stdio, 'error', print)('Unable to add %s as local mirror' % pkg.file_name)
        return None

    def get_all_pkg_info(self):
        return [self.db[key] for key in self.db]

    def get_rpm_pkg_by_info(self, pkg_info):
        self.stdio and getattr(self.stdio, 'verbose', print)('get RPM package by %s' % pkg_info)
        return Package(pkg_info.path)

    def get_pkgs_info(self, **pattern):
        matchs = self.get_pkgs_info_with_score(**pattern)
        if matchs:
            return [info for info in sorted(matchs, key=lambda x: x[1], reverse=True)]
        return matchs

    def get_best_pkg_info(self, **pattern):
        matchs = self.get_pkgs_info_with_score(**pattern)
        if matchs:
            return Package(max(matchs, key=lambda x: x[1])[0].path)
        return None

    def get_exact_pkg_info(self, **pattern):
        if 'md5' in pattern and pattern['md5']:
            self.stdio and getattr(self.stdio, 'verbose', print)('md5 is %s' % pattern['md5'])
            return self.db[pattern['md5']] if pattern['md5'] in self.db else None
        self.stdio and getattr(self.stdio, 'verbose', print)('md5 is None')
        if 'name' not in pattern and not pattern['name']:
            self.stdio and getattr(self.stdio, 'verbose', print)('name is None')
            return None
        name = pattern['name']
        self.stdio and getattr(self.stdio, 'verbose', print)('name is %s' % name)
        arch = getArchList(pattern['arch']) if 'arch' in pattern and pattern['arch'] else _ARCH
        self.stdio and getattr(self.stdio, 'verbose', print)('arch is %s' % arch)
        release = pattern['release'] if 'release' in pattern else None
        self.stdio and getattr(self.stdio, 'verbose', print)('release is %s' % release)
        version = pattern['version'] if 'version' in pattern else None
        self.stdio and getattr(self.stdio, 'verbose', print)('version is %s' % version)
        pkgs = []
        for key in self.db:
            info = self.db[key]
            if info.name != name:
                continue
            if info.arch not in arch:
                continue
            if release and info.release != release:
                continue
            if version and version != info.version:
                continue
            pkgs.append(info)
        if pkgs:
            pkgs.sort()
            return pkgs[-1]
        else:
            return None

    def get_best_pkg_info_with_score(self, **pattern):
        matchs = self.get_pkgs_info_with_score(**pattern)
        if matchs:
            return max(matchs, key=lambda x: x[1])
        return None

    def get_pkgs_info_with_score(self, **pattern):
        matchs = []
        if 'md5' in pattern and pattern['md5']:
            self.stdio and getattr(self.stdio, 'verbose', print)('md5 is %s' % pattern['md5'])
            return [self.db[pattern['md5']], (0xfffffffff, )] if pattern['md5'] in self.db else matchs
        self.stdio and getattr(self.stdio, 'verbose', print)('md5 is None')
        if 'name' not in pattern and not pattern['name']:
            return matchs
        self.stdio and getattr(self.stdio, 'verbose', print)('name is %s' % pattern['name'])
        if 'arch' in pattern and pattern['arch']:
            pattern['arch'] = getArchList(pattern['arch'])
        else:
            pattern['arch'] = _ARCH
        self.stdio and getattr(self.stdio, 'verbose', print)('arch is %s' % pattern['arch'])
        if 'version' in pattern and pattern['version']:
            pattern['version'] += '.'
        else:
            pattern['version'] = None
        self.stdio and getattr(self.stdio, 'verbose', print)('version is %s' % pattern['version'])
        for key in self.db:
            info = self.db[key]
            if pattern['name'] in info.name:
                matchs.append([info, self.match_score(info, **pattern)])
        return matchs

    def match_score(self, info, name, arch, version=None):
        if info.arch not in arch:
            return [0, ]
        info_version = '%s.' % info.version
        if version and info_version.find(version) != 0:
            return [0 ,]
            
        c = [len(name) / len(info.name), info]
        return c

    def get_info_list(self):
        return [self.db[key] for key in self.db]


class MirrorRepositoryManager(Manager):

    RELATIVE_PATH = 'mirror'

    def __init__(self, home_path, stdio=None):
        super(MirrorRepositoryManager, self).__init__(home_path, stdio=stdio)
        self.remote_path = os.path.join(self.path, 'remote') # rpm remote mirror cache
        self.local_path = os.path.join(self.path, 'local')
        self.is_init = self.is_init and self._mkdir(self.remote_path) and self._mkdir(self.local_path)
        self._local_mirror = None

    @property
    def local_mirror(self):
        if self._local_mirror is None:
            self._local_mirror = LocalMirrorRepository(self.local_path, self.stdio)
        return self._local_mirror

    def get_remote_mirrors(self):
        mirrors = []
        server_vars = deepcopy(_SERVER_VARS)
        linux_id = server_vars.get('ID')
        if linux_id in SUP_MAP:
            version = [int(vnum) for vnum in server_vars.get('VERSION_ID', '').split('.')]
            for vid, elvid in SUP_MAP[linux_id]:
                if version < vid:
                    break
                server_vars['releasever'] = elvid
            server_vars['releasever'] = str(elvid)
            self.stdio and getattr(self.stdio, 'warn', print)('Use centos %s remote mirror repository for %s %s' % (server_vars['releasever'], linux_id, server_vars.get('VERSION_ID')))

        for path in glob(os.path.join(self.remote_path, '*.repo')):
            repo_age = os.stat(path)[8]
            with open(path, 'r') as confpp_obj:
                parser = ConfigParser()
                parser.readfp(confpp_obj)
                for section in parser.sections():
                    if section in ['main', 'installed']:
                        continue
                    bad = RemoteMirrorRepository.validate_repoid(section)
                    if bad:
                        continue
                    meta_data = {}
                    for attr in parser.options(section):
                        value = parser.get(section, attr)
                        meta_data[attr] = value
                    if 'enabled' in meta_data and not meta_data['enabled']:
                        continue
                    if 'baseurl' not in meta_data:
                        continue
                    if 'name' not in meta_data:
                        meta_data['name'] = section
                    if 'repo_age' not in meta_data:
                        meta_data['repo_age'] = repo_age
                    meta_data['name'] = RemoteMirrorRepository.var_replace(meta_data['name'], server_vars)
                    meta_data['baseurl'] = RemoteMirrorRepository.var_replace(meta_data['baseurl'], server_vars)
                    mirror_path = os.path.join(self.remote_path, meta_data['name'])
                    mirror = RemoteMirrorRepository(mirror_path, meta_data, self.stdio)
                    mirrors.append(mirror)
        return mirrors

    def get_mirrors(self):
        mirros = self.get_remote_mirrors()
        mirros.append(self.local_mirror)
        return mirros

    def get_exact_pkg(self, **pattern):
        only_info = 'only_info' in pattern and pattern['only_info']
        mirrors = self.get_mirrors()
        info = [None, None]
        for mirror in mirrors:
            new_one = mirror.get_exact_pkg_info(**pattern)
            self.stdio.verbose('%s found pkg: %s' % (mirror, new_one))
            if new_one and new_one > info[0]:
                info = [new_one, mirror]
        return info[0] if info[0] is None or only_info else info[1].get_rpm_pkg_by_info(info[0])

    def get_best_pkg(self, **pattern):
        if 'fuzzy' not in pattern or not pattern['fuzzy']:
            return self.get_exact_pkg(**pattern)
        only_info = 'only_info' in pattern and pattern['only_info']
        mirrors = self.get_mirrors()
        best = None
        source_mirror = None
        for mirror in mirrors:
            t_best = mirror.get_best_pkg_info_with_score(**pattern)
            self.stdio.verbose('%s found pkg: %s' % (mirror, t_best))
            if best is None:
                best = t_best
                source_mirror = mirror
            elif t_best[1] > best[1]:
                best = t_best
                source_mirror = mirror
        if best:
            return best[0] if only_info else source_mirror.get_rpm_pkg_by_info(best[0])

    def add_remote_mirror(self, src):
        pass

    def add_local_mirror(self, src, force=False):
        self.stdio and getattr(self.stdio, 'verbose', print)('%s is file or not' % src)
        if not os.path.isfile(src):
            self.stdio and getattr(self.stdio, 'error', print)('No such file: %s' % (src))
            return None
        try:
            self.stdio and getattr(self.stdio, 'verbose', print)('load %s to Package Object' % src)
            pkg = Package(src)
        except:
            self.stdio and getattr(self.stdio, 'exception', print)('')
            self.stdio and getattr(self.stdio, 'error', print)('failed to extract info from %s' % src)
            return None

        if self.local_mirror.exist_pkg(pkg) and not force:
            if not self.stdio:
                return None
            if not getattr(self.stdio, 'confirm', False):
                return None
            if not self.stdio.confirm('mirror %s existed. Do you want to overwrite?' % pkg.file_name):
                return None
        self.stdio and getattr(self.stdio, 'print', print)('%s' % pkg)
        return self.local_mirror.add_pkg(pkg)
