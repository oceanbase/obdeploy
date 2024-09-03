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
import tempfile
import time
import pickle
import string
import fcntl
import requests
from glob import glob
from enum import Enum
from copy import deepcopy
from xml.etree import cElementTree

from _stdio import SafeStdio
from ssh import LocalClient
try:
    from ConfigParser import ConfigParser
except:
    from configparser import ConfigParser

from _arch import getArchList, getBaseArch
from _rpm import Version, Package, PackageInfo
from tool import ConfigUtil, FileUtil, var_replace
from _manager import Manager
from tool import timeout


_ARCH = getArchList()
_NO_LSE = 'amd64' in _ARCH and LocalClient.execute_command("grep atomics /proc/cpuinfo").stdout.strip() == ''

def get_use_centos_release(stdio=None):
    _RELEASE = None
    SUP_MAP = {
        'ubuntu': {'16': 7},
        'debian': {'9': 7},
        'opensuse-leap': {'15': 7},
        'sles': {'15.2': 7},
        'fedora': {'33': 7},
        'uos': {'20': 8},
        'anolis': {'23': 7},
        'openEuler': {'22.03': 7},
        'kylin': {'V10': 8},
        'alinux': {'2': 7, '3': 8}
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

    server_vars = deepcopy(_SERVER_VARS)
    linux_id = server_vars.get('ID')
    if linux_id in SUP_MAP:
        version_id = server_vars.get('VERSION_ID', '')
        sorted_versions = sorted([Version(key) for key in SUP_MAP[linux_id]], reverse=True)
        for version in sorted_versions:
            if Version(version_id) >= version:
                server_vars['releasever'] = SUP_MAP[linux_id][str(version)]
                break
        else:
            server_vars['releasever'] = SUP_MAP[linux_id][str(version)]
        stdio and getattr(stdio, 'warn', print)('Use centos %s remote mirror repository for %s %s' % (server_vars['releasever'], linux_id, server_vars.get('VERSION_ID')))
    use_release = server_vars.get('releasever')
    return use_release, server_vars


class MirrorRepositoryType(Enum):

    LOCAL = 'local'
    REMOTE = 'remote'


class MirrorRepository(SafeStdio):
    
    MIRROR_TYPE = None
    __VERSION_KEY__ = '__version__'

    def __init__(self, mirror_path, stdio=None):
        self.stdio = stdio
        self.mirror_path = mirror_path
        self.name = os.path.split(mirror_path)[1]
        self.section_name = self.name
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

    def _pattern_check(self, pkg, **pattern):
        for key in ['md5', 'name', 'version', 'release', 'arch']:
            if pattern.get(key) is not None and getattr(pkg, key) != pattern[key]:
                self.stdio and getattr(self.stdio, 'verbose', print)('pkg %s is %s, but %s is required' % (key, getattr(pkg, key), pattern[key]))
                return None
        return pkg

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

    def get_all_rpm_pkgs(self):
        pkgs = set()
        for file_path in glob(os.path.join(self.mirror_path, '*.rpm')):
            try:
                pkgs.add(Package(file_path))
            except:
                self.stdio.exception()
                self.stdio.verbose("Failed to open rpm file: %s" % file_path)
        return pkgs


class RemotePackageInfo(PackageInfo):

    def __init__(self, elem):
        self.epoch = None
        self.location = (None, None)
        self.checksum = (None,None) # type,value
        self.openchecksum = (None,None) # type,value
        self.time = (None, None)
        self.package_size = None
        super(RemotePackageInfo, self).__init__(None, None, None, None, None, None)
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

            elif child_name == 'size':
                self.size = int(child.attrib.get('installed'))
                self.package_size = int(child.attrib.get('package'))


class RemoteMirrorRepository(MirrorRepository):
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
                    delta = RemoteMirrorRepository.RepoData(child)
                    delta.type = self.type
                    self.deltas.append(delta)

    MIRROR_TYPE = MirrorRepositoryType.REMOTE
    REMOTE_REPOMD_FILE = '/repodata/repomd.xml'
    REPOMD_FILE = 'repomd.xml'
    OTHER_DB_FILE = 'other_db.xml'
    REPO_AGE_FILE = '.rege_age'
    DB_CACHE_FILE = '.db'
    PRIMARY_REPOMD_TYPE = 'primary'
    __VERSION__ = Version("1.0")

    def __init__(self, mirror_path, meta_data, stdio=None):
        self.baseurl = None
        self.repomd_age = 0
        self.repo_age = 0
        self.priority = 1
        self.gpgcheck = False
        self._db = None
        self._repomds = None
        self._available = None
        super(RemoteMirrorRepository, self).__init__(mirror_path, stdio=stdio)
        self.section_name = meta_data['section_name']
        self.baseurl = meta_data['baseurl']
        self.enabled = meta_data['enabled'] == '1'
        self.gpgcheck = ConfigUtil.get_value_from_dict(meta_data, 'gpgcheck', 0, int) > 0
        self.priority = 100 - ConfigUtil.get_value_from_dict(meta_data, 'priority', 99, int)
        if os.path.exists(mirror_path):
            self._load_repo_age()
        if self.enabled:
            repo_age = ConfigUtil.get_value_from_dict(meta_data, 'repo_age', 0, int)
            if (repo_age > self.repo_age or int(time.time()) - 86400 > self.repo_age) and self.available:
                if self.update_mirror():
                    self.repo_age = repo_age
        
    @property
    def available(self):
        if not self.enabled:
            return False
        if self._available is None:
            try:
                with timeout(5):
                    req = requests.request('get', self.baseurl)
                    self._available = req.status_code < 400
            except Exception:
                self.stdio and getattr(self.stdio, 'exception', print)('')
                self._available = False
        return self._available

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
        self._load_db_cache(file_path)
        if self._db is None:
            fp = FileUtil.unzip(file_path, stdio=self.stdio)
            if not fp:
                FileUtil.rm(file_path, stdio=self.stdio)
                return []
            self._db = {}
            try:
                parser = cElementTree.iterparse(fp)
                for event, elem in parser:
                    if RemoteMirrorRepository.ns_cleanup(elem.tag) == 'package' and elem.attrib.get('type') == 'rpm':
                        info = RemotePackageInfo(elem)
                        self._db[info.md5] = info
                self._dump_db_cache()
            except:
                FileUtil.rm(file_path, stdio=self.stdio)
                self.stdio and self.stdio.critical('failed to parse file %s, please retry later.' % file_path)
                return []
        return self._db

    def _load_db_cache(self, path):
        try:
            db_cacahe_path = self.get_db_cache_file(self.mirror_path)
            repomd_time = os.stat(path)[8]
            cache_time = os.stat(db_cacahe_path)[8]
            if cache_time > repomd_time:
                self.stdio and getattr(self.stdio, 'verbose', print)('load %s' % db_cacahe_path)
                with open(db_cacahe_path, 'rb') as f:
                    self._db = pickle.load(f)
                    if self.__VERSION__ > Version(self.db.get(self.__VERSION_KEY__, '0')):
                        self._db = None
                    else:
                        del self._db[self.__VERSION_KEY__]
        except:
            pass

    def _dump_db_cache(self):
        if self._db:
            data = deepcopy(self.db)
            data[self.__VERSION_KEY__] = self.__VERSION__
            try:
                db_cacahe_path = self.get_db_cache_file(self.mirror_path)
                self.stdio and getattr(self.stdio, 'verbose', print)('dump %s' % db_cacahe_path)
                with open(db_cacahe_path, 'wb') as f:
                    pickle.dump(data, f)
                return True
            except:
                self.stdio.exception('')
                pass
            return False

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
    def get_db_cache_file(mirror_path):
        return os.path.join(mirror_path, RemoteMirrorRepository.DB_CACHE_FILE)

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
            self._available = False
            self.stdio and getattr(self.stdio, 'stop_loading')('fail')
            return False
        file_path = self._get_repomd_data_file(primary_repomd)
        if not file_path:
            self._available = False
            self.stdio and getattr(self.stdio, 'stop_loading')('fail')
            return False
        self._db = None
        self.repo_age = int(time.time())
        self._dump_repo_age_data()
        self.stdio and getattr(self.stdio, 'stop_loading')('succeed')
        self._available = True
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

    def get_rpm_info_by_md5(self, md5, **pattern):
        if md5 in self.db:
            return self._pattern_check(self.db[md5], **pattern)
        for key in self.db:
            info = self.db[key]
            if info.md5 == md5:
                self.stdio and getattr(self.stdio, 'verbose', print)('%s translate info %s' % (md5, info.md5))
                return self._pattern_check(info, **pattern)
        return None

    def get_rpm_pkg_by_info(self, pkg_info):
        file_name = pkg_info.location[1]
        file_path = os.path.join(self.mirror_path, file_name)
        self.stdio and getattr(self.stdio, 'verbose', print)('get RPM package by %s' % pkg_info)
        if not os.path.exists(file_path) or os.stat(file_path)[8] < pkg_info.time[1] or os.path.getsize(file_path) != pkg_info.package_size:
            base_url = pkg_info.location[0] if pkg_info.location[0] else self.baseurl
            url = '%s/%s' % (base_url, pkg_info.location[1])
            if not self.download_file(url, file_path, self.stdio):
                return None
        return Package(file_path)
    
    def get_pkgs_info(self, **pattern):
        matchs = self.get_pkgs_info_with_score(**pattern)
        if matchs:
            return [info[0] for info in sorted(matchs, key=lambda x: x[1], reverse=True)]
        return matchs

    def get_best_pkg_info(self, **pattern):
        matchs = self.get_pkgs_info_with_score(**pattern)
        if matchs:
            return Package(max(matchs, key=lambda x: x[1])[0].path)
        return None

    def get_exact_pkg_info(self, **pattern):
        if 'md5' in pattern and pattern['md5']:
            self.stdio and getattr(self.stdio, 'verbose', print)('md5 is %s' % pattern['md5'])
            return self.get_rpm_info_by_md5(**pattern)
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
        version = ConfigUtil.get_value_from_dict(pattern, 'version', transform_func=Version)
        self.stdio and getattr(self.stdio, 'verbose', print)('version is %s' % version)
        min_version = ConfigUtil.get_value_from_dict(pattern, 'min_version', transform_func=Version)
        self.stdio and getattr(self.stdio, 'verbose', print)('min_version is %s' % min_version)
        max_version = ConfigUtil.get_value_from_dict(pattern, 'max_version', transform_func=Version)
        self.stdio and getattr(self.stdio, 'verbose', print)('max_version is %s' % max_version)
        only_download = pattern['only_download'] if 'only_download' in pattern else False
        self.stdio and getattr(self.stdio, 'verbose', print)('only_download is %s' % only_download)
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
            if min_version and min_version > info.version:
                continue
            if max_version and max_version <= info.version:
                continue
            if only_download and not self.is_download(info):
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
            return [info[0] for info in sorted(matchs, key=lambda x: x[1], reverse=True)]
        return None

    def get_pkgs_info_with_score(self, **pattern):
        matchs = []
        if 'md5' in pattern and pattern['md5']:
            self.stdio and getattr(self.stdio, 'verbose', print)('md5 is %s' % pattern['md5'])
            info = None
            if pattern['md5'] in self.db:
                info = self._pattern_check(self.db[pattern['md5']], **pattern)
            return [info, (0xfffffffff, )] if info else matchs
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
        release = pattern['release'] if 'release' in pattern else None
        self.stdio and getattr(self.stdio, 'verbose', print)('release is %s' % release)
        if 'version' in pattern and pattern['version']:
            pattern['version'] += '.'
        else:
            pattern['version'] = None
        self.stdio and getattr(self.stdio, 'verbose', print)('version is %s' % pattern['version'])
        for key in self.db:
            info = self.db[key]
            if pattern['name'] in info.name:
                score = self.match_score(info, **pattern)
                if score[0]:
                    matchs.append([info, score])
        return matchs

    def match_score(self, info, name, arch, version=None, min_version=None, max_version=None, release=None):
        if info.arch not in arch:
            return [0, ]
        info_version = '%s.' % info.version
        if version and info_version.find(version) != 0:
            return [0 ,]
        if min_version and Version(info_version) <= Version(min_version):
            return [0 ,]
        if max_version and Version(info_version) > Version(max_version):
            return [0 ,]
        if release and info.release != release:
            return [0 ,]

        if _NO_LSE:
            lse_score = 'nonlse' in info.release
        else:
            lse_score = True

        c = [len(name) / len(info.name), lse_score, info]
        return c

    def is_download(self, pkg_info):
        file_name = pkg_info.location[1]
        file_path = os.path.join(self.mirror_path, file_name)
        return os.path.exists(file_path)


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
                with FileUtil.open(save_path, "wb", stdio=stdio) as fw:
                    for chunk in fget.iter_content(chunk_size):
                        fw.write(chunk)
                        file_done = file_done + chunk_size
                        if print_bar and file_done <= file_size:
                            stdio.update_progressbar(file_done)
                    print_bar and stdio.finish_progressbar()
            return True
        except:
            FileUtil.rm(save_path)
            stdio and getattr(stdio, 'warn', print)('Failed to download %s to %s' % (url, save_path))
            stdio and getattr(stdio, 'exception', print)('')
        return False

class LocalMirrorRepository(MirrorRepository):

    MIRROR_TYPE = MirrorRepositoryType.LOCAL
    _DB_FILE = '.db'
    __VERSION__ = Version("1.0")

    def __init__(self, mirror_path, stdio=None):
        super(LocalMirrorRepository, self).__init__(mirror_path, stdio=stdio)
        self.db = {}
        self.db_path = os.path.join(mirror_path, self._DB_FILE)
        self.enabled = '-'
        self.available = True
        self._load_db()

    @property
    def repo_age(self):
        return int(time.time())

    def _load_db(self):
        try:
            if os.path.isfile(self.db_path):
                with open(self.db_path, 'rb') as f:
                    db = pickle.load(f)
                    self._flush_db(db)
        except:
            self.stdio.exception('')
            pass
        
    def _flush_db(self, db):
        need_flush = self.__VERSION__ > Version(db.get(self.__VERSION_KEY__, '0')) 
        for key in db:
            data = db[key]
            path = getattr(data, 'path', False)
            if not path or not os.path.exists(path):
                continue
            if need_flush:
                data = Package(path)
            self.db[key] = data
        if need_flush:
            self._dump_db()

    def _dump_db(self):
        # 所有 dump方案都为临时
        try:
            data = deepcopy(self.db)
            data[self.__VERSION_KEY__] = self.__VERSION__
            with open(self.db_path, 'wb') as f:
                pickle.dump(data, f)
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
            self.stdio and getattr(self.stdio, 'exception', print)('')
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
            return [info[0] for info in sorted(matchs, key=lambda x: x[1], reverse=True)]
        return matchs

    def get_best_pkg_info(self, **pattern):
        matchs = self.get_pkgs_info_with_score(**pattern)
        if matchs:
            return Package(max(matchs, key=lambda x: x[1])[0].path)
        return None

    def get_exact_pkg_info(self, **pattern):
        if 'md5' in pattern and pattern['md5']:
            self.stdio and getattr(self.stdio, 'verbose', print)('md5 is %s' % pattern['md5'])
            info = None
            if pattern['md5'] in self.db:
                info = self._pattern_check(self.db[pattern['md5']], **pattern)
            return info
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
        version = ConfigUtil.get_value_from_dict(pattern, 'version', transform_func=Version)
        self.stdio and getattr(self.stdio, 'verbose', print)('version is %s' % version)
        min_version = ConfigUtil.get_value_from_dict(pattern, 'min_version', transform_func=Version)
        self.stdio and getattr(self.stdio, 'verbose', print)('min_version is %s' % min_version)
        max_version = ConfigUtil.get_value_from_dict(pattern, 'max_version', transform_func=Version)
        self.stdio and getattr(self.stdio, 'verbose', print)('max_version is %s' % max_version)
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
            if min_version and min_version > info.version:
                continue
            if max_version and max_version <= info.version:
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
            info = None
            if pattern['md5'] in self.db:
                info = self._pattern_check(self.db[pattern['md5']], **pattern)
            return [info, (0xfffffffff, )] if info else matchs
        self.stdio and getattr(self.stdio, 'verbose', print)('md5 is None')
        if 'name' not in pattern and not pattern['name']:
            return matchs
        self.stdio and getattr(self.stdio, 'verbose', print)('name is %s' % pattern['name'])
        if 'arch' in pattern and pattern['arch']:
            pattern['arch'] = getArchList(pattern['arch'])
        else:
            pattern['arch'] = _ARCH
        self.stdio and getattr(self.stdio, 'verbose', print)('arch is %s' % pattern['arch'])
        release = pattern['release'] if 'release' in pattern else None
        self.stdio and getattr(self.stdio, 'verbose', print)('release is %s' % release)
        if 'version' in pattern and pattern['version']:
            pattern['version'] += '.'
        else:
            pattern['version'] = None
        self.stdio and getattr(self.stdio, 'verbose', print)('version is %s' % pattern['version'])
        for key in self.db:
            info = self.db[key]
            if pattern['name'] in info.name:
                score = self.match_score(info, **pattern)
                if score[0]:
                    matchs.append([info, score])
        return matchs

    def match_score(self, info, name, arch, version=None, min_version=None, max_version=None, release=None):
        if info.arch not in arch:
            return [0, ]
        info_version = '%s.' % info.version
        if version and info_version.find(version) != 0:
            return [0 ,]
        if min_version and Version(info_version) <= Version(min_version):
            return [0 ,]
        if max_version and Version(info_version) > Version(max_version):
            return [0 ,]
        if release and info.release != release:
            return [0 ,]

        c = [len(name) / len(info.name), info]
        return c

    def get_info_list(self):
        return [self.db[key] for key in self.db]


class MirrorRepositoryConfig(object):

    def __init__(self, path, parser, repo_age):
        self.path = path
        self.parser = parser
        self.repo_age = repo_age
        self.sections = {}

    def add_section(self, section):
        self.sections[section.section_name] = section

    def __eq__(self, o):
        return self.repo_age == o.repo_age

    def __le__(self, o):
        return self.repo_age < o.repo_age

    def __gt__(self, o):
        return self.repo_age > o.repo_age


class MirrorRepositorySection(object):

    def __init__(self, section_name, meta_data, remote_path):
        self.section_name = section_name
        self.meta_data = meta_data
        self.remote_path = remote_path

    def get_mirror(self, server_vars, stdio=None):
        meta_data = self.meta_data
        meta_data['name'] = var_replace(meta_data['name'], server_vars)
        meta_data['baseurl'] = var_replace(meta_data['baseurl'], server_vars)
        mirror_path = os.path.join(self.remote_path, meta_data['name'])
        mirror = RemoteMirrorRepository(mirror_path, meta_data, stdio)
        return mirror

    @property
    def is_enabled(self):
        return self.meta_data.get('enabled', '1') == '1'


class MirrorRepositoryManager(Manager):

    RELATIVE_PATH = 'mirror'

    def __init__(self, home_path, lock_manager=None, stdio=None):
        super(MirrorRepositoryManager, self).__init__(home_path, stdio=stdio)
        self.remote_path = os.path.join(self.path, 'remote') # rpm remote mirror cache
        self.local_path = os.path.join(self.path, 'local')
        self.is_init = self.is_init and self._mkdir(self.remote_path) and self._mkdir(self.local_path)
        self._local_mirror = None
        self.lock_manager = lock_manager
        self._cache_path_repo_config = {}
        self._cache_section_repo_config = {}

    def _lock(self, read_only=False):
        if self.lock_manager:
            if read_only:
                return self.lock_manager.mirror_and_repo_sh_lock()
            else:
                return self.lock_manager.mirror_and_repo_ex_lock()
        return True

    @property
    def local_mirror(self):
        self._lock()
        if self._local_mirror is None:
            self._local_mirror = LocalMirrorRepository(self.local_path, self.stdio)
        return self._local_mirror

    def _get_repo_config(self, path):
        self.stdio and getattr(self.stdio, 'verbose', print)('load repo config: %s' % path)
        repo_conf = self._cache_path_repo_config.get(path)
        repo_age = os.stat(path)[8]
        if not repo_conf or repo_age != repo_conf.repo_age:
            with FileUtil.open(path, 'r', stdio=self.stdio) as confpp_obj:
                parser = ConfigParser()
                parser.readfp(confpp_obj)
                repo_conf = MirrorRepositoryConfig(path, parser, repo_age)
                self._cache_path_repo_config[path] = repo_conf
        return self._cache_path_repo_config[path]

    def _get_repo_config_by_section(self, section_name):
        return self._cache_section_repo_config.get(section_name)

    def _remove_cache(self, section_name):
        repo_conf = self._cache_section_repo_config[section_name]
        del self._cache_path_repo_config[repo_conf.path]
        del self._cache_section_repo_config[section_name]

    def _scan_repo_configs(self):
        cached_sections = list(self._cache_section_repo_config.keys())
        for path in glob(os.path.join(self.remote_path, '*.repo')):
            repo_conf = self._get_repo_config(path)
            for section in repo_conf.parser.sections():
                if section in ['main', 'installed']:
                    continue
                if section in ['local', 'remote']:
                    self.stdio and getattr(self.stdio, 'warn', print)('%s is system keyword.' % section)
                    continue
                bad = RemoteMirrorRepository.validate_repoid(section)
                if bad:
                    continue
                meta_data = {'section_name': section}
                for attr in repo_conf.parser.options(section):
                    value = repo_conf.parser.get(section, attr)
                    meta_data[attr] = value
                if 'enabled' not in meta_data:
                    meta_data['enabled'] = '1'
                if 'baseurl' not in meta_data:
                    continue
                if 'name' not in meta_data:
                    meta_data['name'] = section
                if 'repo_age' not in meta_data:
                    meta_data['repo_age'] = repo_conf.repo_age
                mirror_section = MirrorRepositorySection(section, meta_data, self.remote_path)
                repo_conf.add_section(mirror_section)
                self._cache_section_repo_config[section] = repo_conf
                if section in cached_sections:
                    cached_sections.remove(section)
        if cached_sections:
            for miss_section in cached_sections:
                self._remove_cache(miss_section)

    def _get_sections(self):
        self._scan_repo_configs()
        sections = {}
        for repo_conf in sorted(self._cache_path_repo_config.values()):
            sections.update(repo_conf.sections)
        return sections.values()

    def _get_section(self, section_name):
        self._scan_repo_configs()
        repo_conf = self._get_repo_config_by_section(section_name)
        if not repo_conf:
            return None
        return repo_conf.sections.get(section_name)


    def get_remote_mirrors(self, is_enabled=True):
        self._lock()
        mirrors = []
        for mirror_section in self._get_sections():
            if is_enabled is not None and is_enabled != mirror_section.is_enabled:
                continue
            _, server_vars = get_use_centos_release(self.stdio)
            mirrors.append(mirror_section.get_mirror(server_vars, self.stdio))
        return mirrors

    def get_mirrors(self, is_enabled=True):
        self._lock()
        mirrors = self.get_remote_mirrors(is_enabled=is_enabled)
        mirrors.insert(0, self.local_mirror)
        return mirrors

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

    def get_pkgs_info(self, name, **pattern):
        pkgs = set()
        mirrors = self.get_mirrors()
        for mirror in mirrors:
            for pkg in mirror.get_pkgs_info(name=name, **pattern):
                if pkg.name != name:
                    break
                pkgs.add(pkg)
        return pkgs

    def add_remote_mirror(self, src):
        pass

    def add_local_mirror(self, src, force=False):
        self._lock()
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

    def set_remote_mirror_enabled(self, section_name, enabled=True):
        self._lock()
        op = 'Enable' if enabled else 'Disable'
        enabled_str = '1' if enabled else '0'
        self.stdio and getattr(self.stdio, 'start_loading')('%s %s' % (op, section_name))
        if section_name == 'local':
            self.stdio and getattr(self.stdio, 'error', print)('Local mirror repository CANNOT BE %sD.' % op.upper())
            return False
        if section_name == 'remote':
            self._scan_repo_configs()
            for repo_config in self._cache_path_repo_config.values():
                for section_name in repo_config.sections.keys():
                    repo_config.parser.set(section_name, 'enabled', enabled_str)
                with FileUtil.open(repo_config.path, 'w', stdio=self.stdio) as confpp_obj:
                    fcntl.flock(confpp_obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    repo_config.parser.write(confpp_obj)
                repo_age = os.stat(repo_config.path)[8]
                repo_config.repo_age = repo_age
                for mirror_section in repo_config.sections.values():
                    mirror_section.meta_data['enabled'] = enabled_str
                    mirror_section.meta_data['repo_age'] = repo_age
            self.stdio and getattr(self.stdio, 'stop_loading')('succeed')
            return True
        else:
            mirror_section = self._get_section(section_name)
            if not mirror_section:
                self.stdio and getattr(self.stdio, 'error', print)('%s not found.' % (section_name))
                self.stdio and getattr(self.stdio, 'stop_loading')('fail')
                return False
            if mirror_section.is_enabled == enabled:
                self.stdio and getattr(self.stdio, 'print', print)('%s is already %sd' % (section_name, op.lower()))
                self.stdio and getattr(self.stdio, 'stop_loading')('succeed')
                return True
            repo_config = self._get_repo_config_by_section(section_name)
            if not repo_config:
                self.stdio and getattr(self.stdio, 'error', print)('%s not found.' % (section_name))
                self.stdio and getattr(self.stdio, 'stop_loading')('fail')
                return False

            repo_config.parser.set(section_name, 'enabled', enabled_str)
            with FileUtil.open(repo_config.path, 'w', stdio=self.stdio) as confpp_obj:
                fcntl.flock(confpp_obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
                repo_config.parser.write(confpp_obj)

            repo_age = os.stat(repo_config.path)[8]
            repo_config.repo_age = repo_age
            mirror_section.meta_data['enabled'] = enabled_str
            mirror_section.meta_data['repo_age'] = repo_age
            self.stdio and getattr(self.stdio, 'stop_loading')('succeed')
        return True

    def add_repo(self, url):
        self._lock()
        download_file_save_name = url.split('/')[-1]
        if not download_file_save_name.endswith(".repo"):
            self.stdio.error("Can't download. Please use a file in .repo format.")
            return False

        download_file_save_path = os.path.join(self.remote_path, download_file_save_name)
        
        if os.path.exists(download_file_save_path):
            if not self.stdio.confirm("the repo file you want to add already exists, overwrite it?"):
                self.stdio.print("exit without any changes")
                return True

        try:
            download_file_res = requests.get(url, timeout=(5, 5))
        except Exception as e:
            self.stdio.exception("Failed to download repository file")
            return False

        download_status_code = download_file_res.status_code
        
        if download_status_code != 200:
            self.stdio.verbose("http code: {}, http body: {}".format(download_status_code, download_file_res.text))
            self.stdio.error("Failed to download repository file")
            return False

        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.repo') as tf:
                tf.write(download_file_res.content.decode(encoding='utf8'))
                tf.seek(0)
                ConfigParser().readfp(tf)
                tf.seek(0)
                if LocalClient.put_file(tf.name, download_file_save_path, stdio=self.stdio):
                    self.stdio.print("repo file saved to {}".format(download_file_save_path))
                    return True
                else:
                    self.stdio.error("Failed to save repository file")
                    return False
        except Exception as e:
            self.stdio.exception("Failed to save repository file")
            return False

    def get_all_rpm_pkgs(self):
        pkgs = list()
        mirrors = self.get_mirrors()
        for mirror in mirrors:
            pkgs = pkgs + list(mirror.get_all_rpm_pkgs())
        return pkgs

    def delete_pkgs(self, pkgs):
        if not pkgs:
            return True
        for pkg in pkgs:
            if not pkg.path.startswith(self.path):
                self.stdio.error("The path of the %s file does not start with %s." % (pkg.path, self.path))
                return False
            if not FileUtil.rm(pkg.path, self.stdio):
                return False
        return True

