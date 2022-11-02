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
from multiprocessing import cpu_count
from multiprocessing.pool import Pool

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
        self.files = self.get_all_files(files)
        self.path = path
        self.package()

    def __hash__(self):
        return hash(self.path)

    @staticmethod
    def get_all_files(source_files):
        files = {}
        for src_path, target_path in source_files.items():
            if not os.path.isdir(target_path) or os.path.islink(target_path):
                files[src_path] = target_path
            else:
                files[src_path+'/'] = target_path
                for fp in LocalPackage.list_dir(target_path):
                    files[os.path.join(src_path, os.path.relpath(fp, target_path))] = fp
        return files

    @staticmethod
    def list_dir(path):
        files = []
        for fn in os.listdir(path):
            fp = os.path.join(path, fn)
            if not os.path.isdir(fp) or os.path.islink(fp):
                files.append(fp)
            else:
                files += LocalPackage.list_dir(fp)
        return files

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
            if basename:
                basenames.append(basename)
                dirindexes.append(dirnames_map[dirname])
                if os.path.islink(target_path):
                    filemd5s.append('')
                    filelinktos.append(os.readlink(target_path))
                    filemodes.append(-24065)
                else:
                    m_value = FileUtil.checksum(target_path)
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


class ExtractFileInfo(object):

    def __init__(self, src_path, target_path, mode):
        self.src_path = src_path
        self.target_path = target_path
        self.mode = mode


class ParallerExtractWorker(object):

    def __init__(self, pkg, files, stdio=None):
        self.pkg = pkg
        self.files = files
        self.stdio = stdio
    
    @staticmethod
    def extract(worker):
        with worker.pkg.open() as rpm:
            for info in worker.files:
                if os.path.exists(info.target_path):
                    continue
                fd = rpm.extractfile(info.src_path)
                with FileUtil.open(info.target_path, 'wb', stdio=worker.stdio) as f:
                    FileUtil.copy_fileobj(fd, f)
                if info.mode != 0o744:
                    os.chmod(info.target_path, info.mode)


class ParallerExtractor(object):

    MAX_PARALLER = cpu_count() if cpu_count() else 8

    def __init__(self, pkg, files, stdio=None):
        self.pkg = pkg
        self.files = files
        self.stdio = stdio

    def extract(self):
        workers = []
        file_num = len(self.files)
        paraler = int(min(self.MAX_PARALLER, file_num))
        size = min(100, int(file_num / paraler))
        size = int(max(10, size))
        index = 0
        while index < file_num:
            p_index = index + size
            workers.append(ParallerExtractWorker(
                self.pkg,
                self.files[index:p_index],
                stdio=self.stdio
            ))
            index = p_index
        
        pool = Pool(processes=paraler)
        try:
            results = pool.map(ParallerExtractWorker.extract, workers)
            for r in results:
                if not r:
                    return False
        except KeyboardInterrupt:
            if pool:
                pool.close()
                pool = None
        finally:
            pool and pool.close()


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
        return '%s-%s-%s-%s' % (self.name, self.version, self.release, self.hash)

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
            for file_item in plugin.file_list(self):
                if file_item.type == InstallPlugin.FileItemType.BIN:
                    files.append(os.path.join(self.repository_dir, file_item.target_path))
        return files

    def file_list(self, plugin):
        files = []
        if self.version and self.hash:
            for file_item in plugin.file_list(self):
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
                self.install_time = data.get('install_time', 0)
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
        if self.install_time:
            data['install_time'] = self.install_time
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
        if self.hash == pkg.md5 and self.file_check(plugin) and self.install_time > plugin.check_value:
            return True
        self.clear()
        try:
            with pkg.open() as rpm:
                file_map = plugin.file_map(pkg)
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
                
                need_extract_files = []
                for src_path in need_files:
                    if src_path not in files:
                        raise Exception('%s not found in packge' % src_path)
                    target_path = os.path.join(self.repository_dir, need_files[src_path])
                    if os.path.exists(target_path):
                        return
                    idx = files[src_path]
                    if filemd5s[idx]:
                        need_extract_files.append(ExtractFileInfo(
                            src_path,
                            target_path,
                            filemodes[idx] & 0x1ff
                        ))
                    elif filelinktos[idx]:
                        links[target_path] = filelinktos[idx]
                    else:
                        raise Exception('%s is directory' % src_path)
                
                ParallerExtractor(pkg, need_extract_files, stdio=self.stdio).extract()

                for link in links:
                    self.stdio and getattr(self.stdio, 'verbose', print)('link %s to %s' % (links[link], link))
                    os.symlink(links[link], link)
                for n_dir in need_dirs:
                    path = os.path.join(self.repository_dir, need_dirs[n_dir])
                    if not os.path.exists(path) and n_dir[:-1] in dirnames:
                        DirectoryUtil.mkdir(path)
                    if not os.path.isdir(path):
                        raise Exception('%s in %s is not dir.' % (pkg.path, n_dir))
            self.set_version(pkg.version)
            self.set_release(pkg.release)
            self.md5 = pkg.md5
            self.arch = pkg.arch
            self.install_time = time.time()
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

    def search_repository(self, version=None, tag=None, release=None):
        path_pattern = os.path.join(self.repository_dir, version or '*', tag or '*')
        repository = None
        for path in glob(path_pattern):
            n_repository = Repository(self.name, path, self.stdio)
            if release and release != n_repository.release:
                continue
            if n_repository.hash and n_repository > repository:
                repository = n_repository
        return repository

    def get_repository(self, version=None, tag=None, release=None):
        if version or tag or release:
            return self.search_repository(version=version, tag=tag, release=release)
        else:
            return self.search_repository(tag=self.name) or self.search_repository()

    def get_repositories(self, version=None):
        if not version:
            version = '*'
        repositories = []
        path_pattern = os.path.join(self.repository_dir, version, '*')
        for path in glob(path_pattern):
            repository = Repository(self.name, path, self.stdio)
            if repository.hash:
                repositories.append(repository)
        return repositories


class RepositoryManager(Manager):

    RELATIVE_PATH = 'repository'
    # repository目录结构为 ./repository/{component_name}/{version}/{tag or hash}

    def __init__(self, home_path, lock_manager=None, stdio=None):
        super(RepositoryManager, self).__init__(home_path, stdio=stdio)
        self.repositories = {}
        self.component_repositories = {}
        self.lock_manager = lock_manager

    def _lock(self, read_only=False):
        if self.lock_manager:
            if read_only:
                return self.lock_manager.mirror_and_repo_sh_lock()
            else:
                return self.lock_manager.mirror_and_repo_ex_lock()
        return True

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

    def get_repositories(self, name, version=None, instance=True):
        repositories = []
        for repository in self.get_component_repository(name).get_repositories(version):
            if instance and repository.is_shadow_repository() is False:
                repositories.append(repository)
        return repositories

    def get_repositories_view(self, name=None):
        if name:
            repositories = self.get_component_repository(name).get_repositories()
        else:
            repositories = []
            path_pattern = os.path.join(self.path, '*')
            for path in glob(path_pattern):
                _, name = os.path.split(path)
                repositories += self.get_component_repository(name).get_repositories()

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

    def get_component_repository(self, name):
        if name not in self.component_repositories:
            self._lock(True)
            path = os.path.join(self.path, name)
            self.component_repositories[name] = ComponentRepository(name, path, self.stdio)
        return self.component_repositories[name]

    def get_repository(self, name, version=None, tag=None, release=None, package_hash=None, instance=True):
        self.stdio.verbose(
            "Search repository {name} version: {version}, tag: {tag}, release: {release}, package_hash: {package_hash}".format(
                name=name, version=version, tag=tag, release=release, package_hash=package_hash))
        tag = tag or package_hash
        component_repository = self.get_component_repository(name)
        if version and tag:
            repository_dir = os.path.join(self.path, name, version, tag)
            if repository_dir in self.repositories:
                repository = self.repositories[repository_dir]
            else:
                repository = component_repository.get_repository(version=version, tag=tag, release=release)
        else:
            repository = component_repository.get_repository(version=version, tag=tag, release=release)
        if not repository:
            return None
        else:
            if repository.repository_dir not in self.repositories:
                self.repositories[repository.repository_dir] = repository
            else:
                repository = self.repositories[repository.repository_dir]
            if not self._check_repository_pattern(repository, version=version, release=release, hash=package_hash):
                return None
        self.stdio.verbose("Found repository {}".format(repository))
        return self.get_instance_repository_from_shadow(repository) if instance else repository

    def _check_repository_pattern(self, repository, **kwargs):
        for key in ["version", "release", "hash"]:
            current_value = getattr(repository, key)
            if kwargs.get(key) is not None and current_value != kwargs[key]:
                self.stdio.verbose("repository {} is {}, but {} is required".format(key, current_value, kwargs[key]))
                return False
        return True

    def create_instance_repository(self, name, version, _hash):
        path = os.path.join(self.path, name, version, _hash)
        if path not in self.repositories:
            self._lock()
            self._mkdir(path)
            repository = Repository(name, path, self.stdio)
            self.repositories[path] = repository
        return self.repositories[path]

    def get_repository_allow_shadow(self, name, version, tag=None):
        path = os.path.join(self.path, name, version, tag if tag else name)
        if os.path.exists(path):
            if path not in self.repositories:
                self._lock(True)
                self.repositories[path] = Repository(name, path, self.stdio)
            return self.repositories[path]
        repository = Repository(name, path, self.stdio)
        repository.set_version(version)
        return repository

    def create_tag_for_repository(self, repository, tag, force=False):
        if repository.is_shadow_repository():
            return False
        self._lock()
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
        self._lock(True)
        try:
            path = os.readlink(repository.repository_dir)
            if path not in self.repositories:
                self.repositories[path] = Repository(repository.name, path, self.stdio)
            return self.repositories[path]
        except:
            pass
        return None