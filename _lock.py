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

import os
import time
from enum import Enum

from tool import FileUtil
from _manager import Manager
from _errno import LockError


class LockType(Enum):

    MIR_REPO = 'mirror_and_repo'
    DEPLOY = 'deploy'
    GLOBAL = 'global'


class MixLock(object):

    def __init__(self, path, stdio=None):
        self.path = path
        self.stdio = stdio
        self._lock_obj = None
        self._sh_cnt = 0
        self._ex_cnt = 0
    
    def __del__(self):
        self._unlock()

    @property
    def lock_obj(self):
        if self._lock_obj is None or self._lock_obj.closed:
            self._lock_obj = FileUtil.open(self.path, _type='w')
        return self._lock_obj

    @property
    def locked(self):
        return self._sh_cnt or self._ex_cnt

    def _ex_lock(self):
        if self.lock_obj:
            try:
                FileUtil.exclusive_lock_obj(self.lock_obj, stdio=self.stdio)
            except Exception as e:
                raise LockError(e)

    def _sh_lock(self):
        if self.lock_obj:
            try:
                FileUtil.share_lock_obj(self.lock_obj, stdio=self.stdio)
            except Exception as e:
                raise LockError(e)

    def sh_lock(self):
        if not self.locked:
            self._sh_lock()
        self._sh_cnt += 1
        self.stdio and getattr(self.stdio, 'verbose', print)('share lock `%s`, count %s' % (self.path, self._sh_cnt))
        return True

    def ex_lock(self):
        if self._ex_cnt == 0:
            try:
                self._ex_lock()
            except Exception as e:
                if self._sh_cnt:
                    self.lock_escalation(LockManager.TRY_TIMES)
                else:
                    raise LockError(e)
        self._ex_cnt += 1
        self.stdio and getattr(self.stdio, 'verbose', print)('exclusive lock `%s`, count %s' % (self.path, self._ex_cnt))
        return True

    def lock_escalation(self, try_times):
        self.stdio and getattr(self.stdio, 'start_loading', print)('waiting for the lock')
        try:
            self._lock_escalation(try_times)
            self.stdio and getattr(self.stdio, 'stop_loading', print)('succeed')
        except Exception as e:
            self.stdio and getattr(self.stdio, 'stop_loading', print)('fail')
            raise LockError(e)

    def _lock_escalation(self, try_times):
        stdio = self.stdio
        while try_times:
            try:
                if try_times % 1000:
                    self.stdio = None
                else:
                    self.stdio = stdio
                try_times -= 1
                self._ex_lock()
                break
            except KeyboardInterrupt:
                self.stdio = stdio
                raise Exception('fail to get lock')
            except Exception as e:
                if try_times:
                    time.sleep(LockManager.TRY_INTERVAL)
                else:
                    self.stdio = stdio
                    raise LockError(e)
        self.stdio = stdio

    def _sh_unlock(self):
        if self._sh_cnt == 0:
            if self._ex_cnt == 0:
                self._unlock()

    def _ex_unlock(self):
        if self._ex_cnt == 0:
            if self._sh_cnt > 0:
                self._sh_lock()
            else:
                self._unlock()

    def sh_unlock(self):
        if self._sh_cnt > 0:
            self._sh_cnt -= 1
            self.stdio and getattr(self.stdio, 'verbose', print)('share lock %s release, count %s' % (self.path, self._sh_cnt))
            self._sh_unlock()
        return self.locked is False

    def ex_unlock(self):
        if self._ex_cnt > 0:
            self._ex_cnt -= 1
            self.stdio and getattr(self.stdio, 'verbose', print)('exclusive lock %s release, count %s' % (self.path, self._ex_cnt))
            self._ex_unlock()
        return self.locked is False

    def _unlock(self):
        if self._lock_obj:
            FileUtil.unlock(self._lock_obj, stdio=self.stdio)
            self._lock_obj.close()
            self._lock_obj = None
            self._sh_cnt = 0
            self._ex_cnt = 0


class Lock(object):

    def __init__(self, mix_lock):
        self.mix_lock = mix_lock

    def lock(self):
        raise NotImplementedError

    def unlock(self):
        raise NotImplementedError


class SHLock(Lock):

    def lock(self):
        self.mix_lock.sh_lock()

    def unlock(self):
        self.mix_lock.sh_unlock()


class EXLock(Lock):

    def lock(self):
        self.mix_lock.ex_lock()

    def unlock(self):
        self.mix_lock.ex_unlock()


class LockMode(Enum):
    NO_LOCK = 0
    DEPLOY_SHARED_LOCK = 1
    DEFAULT = 2


class LockManager(Manager):

    TRY_TIMES = 6000
    TRY_INTERVAL = 0.01

    RELATIVE_PATH = 'lock/'
    GLOBAL_FN = LockType.GLOBAL.value
    MIR_REPO_FN = LockType.MIR_REPO.value
    DEPLOY_FN_PERFIX = LockType.DEPLOY.value
    LOCKS = {}

    def __init__(self, home_path, stdio=None):
        super(LockManager, self).__init__(home_path, stdio)
        self.locks = []
        self.global_path = os.path.join(self.path, self.GLOBAL_FN)
        self.mir_repo_path = os.path.join(self.path, self.MIR_REPO_FN)
        self.mode = LockMode.DEFAULT

    @staticmethod
    def set_try_times(try_times):
        LockManager.TRY_TIMES = try_times

    @staticmethod
    def set_try_interval(try_interval):
        LockManager.TRY_INTERVAL = try_interval

    def __del__(self):
        for lock in self.locks[::-1]:
            lock.unlock()
        self.locks = None

    def _get_mix_lock(self, path):
        if path not in self.LOCKS:
            self.LOCKS[path] = MixLock(path, stdio=self.stdio)
        return self.LOCKS[path]

    @classmethod
    def shutdown(cls):
        for path in cls.LOCKS:
            cls.LOCKS[path]._unlock()
        cls.LOCKS = None

    def set_lock_mode(self, mode):
        for key in LockMode:
            if key.value == mode:
                mode = key
                break
        if not isinstance(mode, LockMode) or mode not in LockMode:
            getattr(self.stdio, 'verbose', print)('unknown lock mode {}'.format(mode))
            return
        self.stdio and getattr(self.stdio, 'verbose', print)('set lock mode to {}({})'.format(mode.name, mode.value))
        self.mode = mode

    def _lock(self, path, clz):
        if self.mode != LockMode.NO_LOCK:
            mix_lock = self._get_mix_lock(path)
            lock = clz(mix_lock)
            lock.lock()
            self.locks.append(lock)
        return True

    def _sh_lock(self, path):
        return self._lock(path, SHLock)

    def _ex_lock(self, path):
        return self._lock(path, EXLock)

    def global_ex_lock(self):
        return self._ex_lock(self.global_path)

    def global_sh_lock(self):
        return self._sh_lock(self.global_path)

    def mirror_and_repo_ex_lock(self):
        return self._ex_lock(self.mir_repo_path)

    def mirror_and_repo_sh_lock(self):
        return self._sh_lock(self.mir_repo_path)

    def _deploy_lock_fp(self, deploy_name):
        return os.path.join(self.path, '%s_%s' % (self.DEPLOY_FN_PERFIX, deploy_name))

    def deploy_ex_lock(self, deploy_name):
        if self.mode == LockMode.DEPLOY_SHARED_LOCK:
            return self._sh_lock(self._deploy_lock_fp(deploy_name))
        else:
            return self._ex_lock(self._deploy_lock_fp(deploy_name))

    def deploy_sh_lock(self, deploy_name):
        return self._sh_lock(self._deploy_lock_fp(deploy_name))


import atexit
atexit.register(LockManager.shutdown)