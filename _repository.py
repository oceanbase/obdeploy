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
import time
import hashlib
from glob import glob

from _rpm import Package, PackageInfo, Version
from _arch import getBaseArch
from tool import DirectoryUtil, FileUtil, YamlLoader
from _manager import Manager
from _plugin import InstallPlugin


class LocalPackage(Package):

    class RpmObject(object):

        def __init__(self, headers, files):
            self.files = files
            self.opens = {}
            self.headers = headers

        def __exit__(self, *arg, **kwargs):
            for path in self.opens:
                self.opens[path].close()

        def __enter__(self):
            self.__exit__()
            self.opens = {}
            return self

        def extractfile(self, name):
            if name not in self.files:
                raise KeyError("member %s could not be found" % name)
            path = self.files[name]
            if path not in self.opens:
                self.opens[path] = open(path, 'rb')
            return self.opens[path]

    def __init__(self, path, name, version, files, release=None, arch=None):
        self.name = name
        self.set_version(version)
        self.set_release(release if release else time.strftime("%Y%m%d%H%M%S", time.localtime(time.time())))
        self.md5 = None
        self.arch = arch if arch else getBaseArch()
        self.headers = {}
        self.files = files
        self.path = path
        self.package()

    def __hash__(self):
        return hash(self.path)

    def package(self):
        count = 0
        dirnames = []
        filemd5s = []
        filemodes = []
        basenames = []
        dirindexes = []
        filelinktos = []
        dirnames_map = {}
        m_sum = hashlib.md5()
        for src_path in self.files:
            target_path = self.files[src_path]
            dirname, basename = os.path.split(src_path)
            if dirname not in dirnames_map:
                dirnames.append(dirname)
                dirnames_map[dirname] = count
                count += 1
            basenames.append(basename)
            dirindexes.append(dirnames_map[dirname])
            if os.path.islink(target_path):
                filemd5s.append('')
                filelinktos.append(os.readlink(target_path))
                filemodes.append(-24065)
            else:
                m = hashlib.md5()
                with open(target_path, 'rb') as f:
                    m.update(f.read())
                m_value = m.hexdigest().encode(sys.getdefaultencoding())
                m_sum.update(m_value)
                filemd5s.append(m_value)
                filelinktos.append('')
                filemodes.append(os.stat(target_path).st_mode)
        self.headers = {
            'dirnames': dirnames,
            'filemd5s': filemd5s,
            'filemodes': filemodes,
            'basenames': basenames,
            'dirindexes': dirindexes,
            'filelinktos': filelinktos,
        }
        self.md5 = m_sum.hexdigest()

    def open(self):
        return self.RpmObject(self.headers, self.files)


class Repository(PackageInfo):
    
    _DATA_FILE = '.data'

    def __init__(self, name, repository_dir, stdio=None):
        self.repository_dir = repository_dir
        super(Repository, self).__init__(name, None, None, None, None)
        self.stdio = stdio
        self._load()
    
    @property
    def hash(self):
        return self.md5

    def __str__(self):
        return '%s-%s-%s' % (self.name, self.version, self.hash)

    def __hash__(self):
        return hash(self.repository_dir)

    def is_shadow_repository(self):
        if os.path.exists(self.repository_dir):
            return os.path.islink(self.repository_dir)
        return False

    @property
    def data_file_path(self):
        path = os.readlink(self.repository_dir) if os.path.islink(self.repository_dir) else self.repository_dir
        return os.path.join(path, Repository._DATA_FILE)

    def bin_list(self, plugin):
        files = []
        if self.version and self.hash:
            for file_item in plugin.file_list():
                if file_item.type == InstallPlugin.FileItemType.BIN:
                    files.append(os.path.join(self.repository_dir, file_item.target_path))
        return files

    def file_list(self, plugin):
        files = []
        if self.version and self.hash:
            for file_item in plugin.file_list():
                path = os.path.join(self.repository_dir, file_item.target_path)
                if file_item.type == InstallPlugin.FileItemType.DIR:
                    files += DirectoryUtil.list_dir(path)
                else:
                    files.append(path)
        return files

    def file_check(self, plugin):
        for file_path in self.file_list(plugin):
            if not os.path.exists(file_path):
                return False
        return True

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.version == other.version and self.hash == other.hash
        if isinstance(other, dict):
            return self.version == other['version'] and self.hash == other['hash']
        return super(Repository, self).__eq__(other)

    def _load(self):
        try:
            with open(self.data_file_path, 'r') as f:
                data = YamlLoader().load(f)
                self.set_version(data.get('version'))
                self.set_release(data.get('release'))
                self.md5 = data.get('hash')
                self.arch = data.get('arch')
        except:
            pass

    def _parse_path(self):
        if self.is_shadow_repository():
            path = os.readlink(self.repository_dir)
        else:
            path = self.repository_dir
        path = path.strip('/')
        path, _hash = os.path.split(path)
        path, version = os.path.split(path)
        if not self.version:
            self.set_version(version)

    def _dump(self):
        data = {'version': self.version, 'hash': self.hash, 'release': self.release, 'arch': self.arch}
        try:
            with open(self.data_file_path, 'w') as f:
                YamlLoader().dump(data, f)
            return True
        except:
            self.stdio and getattr(self.stdio, 'exception', print)('dump %s to %s failed' % (data, self.data_file_path))
        return False

    def load_pkg(self, pkg, plugin):
        if self.is_shadow_repository():
            self.stdio and getattr(self.stdio, 'print', '%s is a shadow repository' % self)
            return False
        hash_path = os.path.join(self.repository_dir, '.hash')
        if self.hash == pkg.md5 and self.file_check(plugin):
            return True
        self.clear()
        try:
            with pkg.open() as rpm:
                file_map = plugin.file_map
                need_dirs = {}
                need_files = {}
                for src_path in file_map:
                    file_item = file_map[src_path]
                    if file_item.type == InstallPlugin.FileItemType.DIR:
                        if not src_path.endswith('/'):
                            src_path += '/'
                        need_dirs[src_path] = file_item.target_path
                    else:
                        need_files[src_path] = file_item.target_path
                files = {}
                links = {}
                dirnames = rpm.headers.get("dirnames")
                basenames = rpm.headers.get("basenames")
                dirindexes = rpm.headers.get("dirindexes")
                filelinktos = rpm.headers.get("filelinktos")
                filemd5s = rpm.headers.get("filemd5s")
                filemodes = rpm.headers.get("filemodes")
                dirs = sorted(need_dirs.keys(), reverse=True)
                format_str = lambda s: s.decode(errors='replace') if isinstance(s, bytes) else s
                for i in range(len(basenames)):
                    if not filemd5s[i] and not filelinktos[i]:
                        continue
                    dir_path = format_str(dirnames[dirindexes[i]])
                    if not dir_path.startswith('./'):
                        dir_path = '.%s' % dir_path
                    file_name = format_str(basenames[i])
                    path = os.path.join(dir_path, file_name)
                    files[path] = i
                    if path not in need_files:
                        for n_dir in need_dirs:
                            if path.startswith(n_dir):
                                need_files[path] = os.path.join(need_dirs[n_dir], path[len(n_dir):])
                                break
                for src_path in need_files:
                    if src_path not in files:
                        raise Exception('%s not found in packge' % src_path)
                    target_path = os.path.join(self.repository_dir, need_files[src_path])
                    if os.path.exists(target_path):
                        return
                    idx = files[src_path]
                    if filemd5s[idx]:
                        fd = rpm.extractfile(src_path)
                        self.stdio and getattr(self.stdio, 'verbose', print)('extract %s to %s' % (src_path, target_path))
                        with FileUtil.open(target_path, 'wb', self.stdio) as f:
                            FileUtil.copy_fileobj(fd, f)
                        mode = filemodes[idx] & 0x1ff
                        if mode != 0o744:
                            os.chmod(target_path, mode)
                    elif filelinktos[idx]:
                        links[target_path] = filelinktos[idx]
                    else:
                        raise Exception('%s is directory' % src_path)

                for link in links:
                    self.stdio and getattr(self.stdio, 'verbose', print)('link %s to %s' % (links[link], link))
                    os.symlink(links[link], link)
                for n_dir in need_dirs:
                    path = os.path.join(self.repository_dir, need_dirs[n_dir])
                    if not os.path.isdir(path):
                        raise Exception('%s: No such dir: %s' % (pkg.path, n_dir))
            self.set_version(pkg.version)
            self.set_release(pkg.release)
            self.md5 = pkg.md5
            self.arch = pkg.arch
            if self._dump():
                return True
            else:
                self.clear()
        except:
            self.stdio and getattr(self.stdio, 'exception', print)('failed to extract file from %s' % pkg.path)
            self.clear()
        return False

    def clear(self):
        if os.path.exists(self.repository_dir):
            return DirectoryUtil.rm(self.repository_dir, self.stdio) and DirectoryUtil.mkdir(self.repository_dir, stdio=self.stdio)
        return True


class RepositoryVO(object):

    def __init__(self, name, version, release, arch, md5, path, tags=[]):
        self.name = name
        self.version = version
        self.release = release
        self.arch = arch
        self.md5 = md5
        self.path = path
        self.tags = tags


class ComponentRepository(object):

    def __init__(self, name, repository_dir, stdio=None):
        self.repository_dir = repository_dir
        self.stdio = stdio
        self.name = name
        DirectoryUtil.mkdir(self.repository_dir, stdio=stdio)

    def get_instance_repositories(self, version):
        repositories = {}
        for tag in os.listdir(self.repository_dir):
            path = os.path.join(self.repository_dir, tag)
            if os.path.islink(path):
                continue
            repository = Repository(self.name, path, self.stdio)
            if repository.hash:
                repositories[repository.hash] = repository
        return repositories

    def get_shadow_repositories(self, version, instance_repositories={}):
        repositories = {}
        for tag in os.listdir(self.repository_dir):
            path = os.path.join(self.repository_dir, tag)
            if not os.path.islink(path):
                continue
            _, md5 = os.path.split(os.readlink(path))
            if md5 in instance_repositories:
                repositories[tag] = instance_repositories[md5]
            else:
                repository = Repository(self.name, path, self.stdio)
                if repository.hash:
                    repositories[repository.hash] = repository
        return repositories

    def get_repository_by_version(self, version, tag=None):
        if tag:
            return self.get_repository_by_tag(tag, version)
        repository = self.get_repository_by_tag(self.name, version)
        if repository:
            return repository
        path_partten = os.path.join(self.repository_dir, version, tag if tag else '*')
        for path in glob(path_partten):
            n_repository = Repository(self.name, path, self.stdio)
            if n_repository.hash and n_repository > repository:
                repository = n_repository
        return repository

    def get_repository_by_tag(self, tag, version=None):
        path_partten = os.path.join(self.repository_dir, version if version else '*', tag)
        for path in glob(path_partten):
            repository = Repository(self.name, path, self.stdio)
            if repository.hash:
                return repository
        return None

    def get_repository(self, version=None, tag=None):
        if tag:
            return self.get_repository_by_tag(tag, version)
        if version:
            return self.get_repository_by_version(version, tag)
        version = None
        for rep_version in os.listdir(self.repository_dir):
            rep_version = Version(rep_version)
            if rep_version > version:
                version = rep_version
        if version:
            return self.get_repository_by_version(version, tag)
        return None
        
    def get_repositories(self, version=None):
        if not version:
            version = '*'
        repositories = []
        path_partten = os.path.join(self.repository_dir, version, '*')
        for path in glob(path_partten):
            repositories.append(Repository(self.name, path, self.stdio))
        return repositories


class RepositoryManager(Manager):

    RELATIVE_PATH = 'repository'
    # repository目录结构为 ./repository/{component_name}/{version}/{tag or hash}

    def __init__(self, home_path, stdio=None):
        super(RepositoryManager, self).__init__(home_path, stdio=stdio)
        self.repositories = {}
        self.component_repositoies = {}

    def _get_repository_vo(self, repository):
        return RepositoryVO(
            repository.name,
            repository.version,
            repository.release,
            repository.arch,
            repository.md5,
            repository.repository_dir,
            []
        )

    def get_repositories_view(self, name=None):
        if name:
            repositories = self.get_component_repositoy(name).get_repositories()
        else:
            repositories = []
            path_partten = os.path.join(self.path, '*')
            for path in glob(path_partten):
                _, name = os.path.split(path)
                repositories += self.get_component_repositoy(name).get_repositories()

        repositories_vo = {}
        for repository in repositories:
            if repository.is_shadow_repository():
                repository_ist = self.get_instance_repository_from_shadow(repository)
                if repository_ist not in repositories_vo:
                    repositories_vo[repository_ist] = self._get_repository_vo(repository)
                _, tag = os.path.split(repository.repository_dir)
                repositories_vo[repository_ist].tags.append(tag)
            elif repository not in repositories_vo:
                repositories_vo[repository] = self._get_repository_vo(repository)
        return list(repositories_vo.values())

    def get_component_repositoy(self, name):
        if name not in self.component_repositoies:
            path = os.path.join(self.path, name)
            self.component_repositoies[name] = ComponentRepository(name, path, self.stdio)
        return self.component_repositoies[name]

    def get_repository_by_version(self, name, version, tag=None, instance=True):
        if not tag:
            tag = name
        path = os.path.join(self.path, name, version, tag)
        if path not in self.repositories:
            component_repositoy = self.get_component_repositoy(name)
            repository = component_repositoy.get_repository(version, tag)
            if repository:
                self.repositories[repository.repository_dir] = repository
                self.repositories[path] = repository
        else:
            repository = self.repositories[path]
        return self.get_instance_repository_from_shadow(repository) if instance else repository

    def get_repository(self, name, version=None, tag=None, instance=True):
        if version:
            return self.get_repository_by_version(name, version, tag)

        component_repositoy = self.get_component_repositoy(name)
        repository = component_repositoy.get_repository(version, tag)
        if repository:
            self.repositories[repository.repository_dir] = repository
        return self.get_instance_repository_from_shadow(repository) if repository and instance else repository

    def create_instance_repository(self, name, version, _hash):
        path = os.path.join(self.path, name, version, _hash)
        if path not in self.repositories:
            self._mkdir(path)
            repository = Repository(name, path, self.stdio)
            self.repositories[path] = repository
        return self.repositories[path]

    def get_repository_allow_shadow(self, name, version, tag=None):
        path = os.path.join(self.path, name, version, tag if tag else name)
        if os.path.exists(path):
            if path not in self.repositories:
                self.repositories[path] = Repository(name, path, self.stdio)
            return self.repositories[path]
        repository =  Repository(name, path, self.stdio)
        repository.set_version(version)
        return repository

    def create_tag_for_repository(self, repository, tag, force=False):
        if repository.is_shadow_repository():
            return False
        path = os.path.join(self.path, repository.name, repository.version, tag)
        if os.path.exists(path):
            if not os.path.islink(path):
                return False
            src_path = os.readlink(path)
            if os.path.normcase(src_path) == os.path.normcase(repository.repository_dir):
                return True
            if not force:
                return False
            DirectoryUtil.rm(path)
        try:
            os.symlink(repository.repository_dir, path)
            return True
        except:
            pass
        return False

    def get_instance_repository_from_shadow(self, repository):
        if not isinstance(repository, Repository) or not repository.is_shadow_repository():
            return repository
        try:
            path = os.readlink(repository.repository_dir)
            if path not in self.repositories:
                self.repositories[path] = Repository(repository.name, path, self.stdio)
            return self.repositories[path]
        except:
            pass
        return None