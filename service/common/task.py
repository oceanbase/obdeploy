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
import time
import functools
from threading import Lock
from collections import defaultdict
from singleton_decorator import singleton

from enum import auto
from fastapi_utils.enums import StrEnum
from service.common import log
from concurrent.futures import ThreadPoolExecutor, TimeoutError


DEFAULT_TASK_TYPE="undefined"
DEFAULT_TASK_TIMEOUT_SECONDS=3600

def get_task_manager():
    return TaskManager()


class TaskStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    FINISHED = auto()


class TaskResult(StrEnum):
    SUCCESSFUL = auto()
    FAILED = auto()
    # running means task not finished, maybe define another name
    RUNNING = auto()


class TaskInfo(object):
    def __init__(self):
        self.start_time = None
        self.status = TaskStatus.PENDING
        self.end_time = None
        self.result = TaskResult.RUNNING
        self.ret = None
        self.exception = None

    def run(self):
        self.status = TaskStatus.RUNNING
        self.start_time = time.time()

    def finish(self):
        self.status = TaskStatus.FINISHED
        self.end_time = time.time()

    def success(self):
        self.result = TaskResult.SUCCESSFUL
        self.finish()

    def fail(self):
        self.result = TaskResult.FAILED
        self.finish()


@singleton
class TaskManager(object):
    def __init__(self):
        self.all_tasks = defaultdict(dict)
        self.lock = Lock()

    def get_task_info(self, name, task_type=DEFAULT_TASK_TYPE):
        ret = None
        self.lock.acquire()
        if name in self.all_tasks[task_type].keys():
            ret = self.all_tasks[task_type][name]
        self.lock.release()
        return ret

    def del_task_info(self, name, task_type=DEFAULT_TASK_TYPE):
        ret = None
        self.lock.acquire()
        if name in self.all_tasks[task_type].keys():
            del(self.all_tasks[task_type][name])
        self.lock.release()

    def register_task(self, name, task_info, task_type=DEFAULT_TASK_TYPE):
        self.lock.acquire()
        log.get_logger().info("register task %s", name)
        self.all_tasks[task_type][name] = task_info
        self.lock.release()


class AutoRegister(object):
    def __init__(self, task_type=DEFAULT_TASK_TYPE, timeout=DEFAULT_TASK_TIMEOUT_SECONDS):
        self._task_type = task_type
        self._timeout = timeout

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if len(args) < 2:
                raise Exception("lack of parameter task_name")
            name = args[1]
            task_manager = get_task_manager()
            task_info = TaskInfo()
            task_manager.register_task(name, task_info, task_type=self._task_type)
            try:
                log.get_logger().info("start run task %s", name)
                task_info.run()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    try:
                        future.result(timeout=self._timeout)
                    except TimeoutError:
                        future.cancel()
                        msg = "task {0} execution timeout".format(name)
                        log.get_logger().exception(msg)
                        task_info.exception = Exception(msg)
                        task_info.fail()
                        log.get_logger().info("task %s finished timeout", name)
                        return 
                log.get_logger().info("task %s run finished", name)
                task_info.success()
                log.get_logger().info("task %s finished successful", name)
            except BaseException as ex:
                msg = "task {0} got exception".format(name)
                log.get_logger().exception(msg)
                task_info.exception = ex
                task_info.fail()
                log.get_logger().info("task %s finished failed", name)
        return wrapper


class Serial(object):
    def __init__(self, task_type=DEFAULT_TASK_TYPE):
        self._task_type = task_type
        self.lock = Lock()

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ret = None
            self.lock.acquire()
            try:
                ret = func(*args, **kwargs)
            except Exception as ex:
                ret = False, ex
            finally:
                self.lock.release()
                return ret
        return wrapper

