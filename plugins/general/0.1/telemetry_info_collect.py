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

import json
import sys
import time
import uuid
import resource
import hashlib

from tool import NetUtil
from ssh import LocalClient
from const import VERSION, REVISION


shell_command_map = {
    "host_type": 'systemd-detect-virt',
    "_cpu_physical_core_num": 'cat /proc/cpuinfo | grep "physical id" | sort | uniq | wc -l',
    "_per_physical_core_num": 'cat /proc/cpuinfo | grep "cpu cores" | cut -f2 -d: | uniq',
    "cpu_logical_cores": 'cat /proc/cpuinfo | grep "processor" | wc -l',
    "cpu_model_name": 'cat /proc/cpuinfo | grep name | cut -f2 -d: | uniq',
    "cpu_frequency": 'cat /proc/cpuinfo | grep MHz | cut -f2 -d: | uniq',
    "cpu_flags": 'cat /proc/cpuinfo | grep flags | cut -f2 -d: | uniq',
    "memory_total": 'cat /proc/meminfo | grep MemTotal | cut -f2 -d: | uniq',
    "memory_free": 'cat /proc/meminfo | grep MemFree | cut -f2 -d: | uniq',
    "memory_avaiable": 'cat /proc/meminfo | grep MemAvailable | cut -f2 -d: | uniq',
    "os_name": 'cat /etc/os-release | grep "^ID=" | cut -f2 -d=',
    "os_release": 'cat /etc/os-release | grep "^VERSION_ID=" | cut -f2 -d='
}


def shell_command(func):
    def wrapper(*args, **kwargs):
        name = func.__name__
        command = shell_command_map.get(name)
        assert command, f"{name} is not in shell_command.yaml"

        res = LocalClient.execute_command(command)
        kwargs["bash_result"] = res.stdout.strip() if res.code == 0 else None
        return func(*args, **kwargs)

    return wrapper


class BaseInfo:
    @staticmethod
    def reporter():
        return 'obd'

    @staticmethod
    def report_time():
        return time.time()

    @staticmethod
    def event_id():
        return str(uuid.uuid4())


class HostInfo:

    @staticmethod
    def host_ip_hash():
        sha1 = hashlib.sha1()
        sha1.update(NetUtil.get_host_ip().encode())
        return sha1.hexdigest()

    @staticmethod
    @shell_command
    def host_type(*args, **kwargs):
        return kwargs["bash_result"]


class CpuInfo:

    @staticmethod
    @shell_command
    def _cpu_physical_core_num(*args, **kwargs):
        return int(kwargs['bash_result'])

    @staticmethod
    @shell_command
    def _per_physical_core_num(*args, **kwargs):
        return int(kwargs['bash_result'])

    @staticmethod
    def cpu_physical_cores(*args, **kwargs):
        return CpuInfo._cpu_physical_core_num() * CpuInfo._per_physical_core_num()

    @staticmethod
    @shell_command
    def cpu_logical_cores(*args, **kwargs):
        return kwargs["bash_result"]

    @staticmethod
    @shell_command
    def cpu_model_name(*args, **kwargs):
        return kwargs["bash_result"]

    @staticmethod
    @shell_command
    def cpu_frequency(*args, **kwargs):
        return kwargs["bash_result"]

    @staticmethod
    @shell_command
    def cpu_flags(*args, **kwargs):
        return kwargs["bash_result"]


class MemInfo:
    @staticmethod
    @shell_command
    def memory_total(*args, **kwargs):
        return kwargs["bash_result"]

    @staticmethod
    @shell_command
    def memory_free(*args, **kwargs):
        return kwargs["bash_result"]

    @staticmethod
    @shell_command
    def memory_avaiable(*args, **kwargs):
        return kwargs["bash_result"]


class DiskInfo:
    @staticmethod
    def get_disks_info():
        data = []
        sha1 = hashlib.sha1()
        for _ in LocalClient.execute_command("df -h | awk '{if(NR>1)print}'").stdout.strip().split('\n'):
            _disk_info = {}
            _ = [i for i in _.split(' ') if i != '']
            _disk_info['deviceName'] = _[0]
            _disk_info['total'] = _[1]
            _disk_info['used'] = _[2]
            sha1.update(_[5].encode())
            _disk_info['mountHash'] = sha1.hexdigest()
            data.append(_disk_info)
        return data


class OsInfo:
    @staticmethod
    @shell_command
    def os_name(*args, **kwargs):
        return kwargs["bash_result"].replace('\"', '')

    @staticmethod
    @shell_command
    def os_release(*args, **kwargs):
        return kwargs["bash_result"].replace('\"', '')


class MachineInfo:

    @staticmethod
    def get_nofile():
        res = resource.getrlimit(resource.RLIMIT_NOFILE)
        return {'nofileSoft': res[0], 'nofileHard': res[1]}


class ObdInfo:
    @staticmethod
    def obd_type():
        return sys.argv[0]

    @staticmethod
    def obd_version(*args, **kwargs):
        return VERSION

    @staticmethod
    def obd_revision(*args, **kwargs):
        return REVISION


def telemetry_machine_data():
    data = {}
    data['reporter'] = BaseInfo.reporter()
    data['reportTime'] = BaseInfo.report_time()
    data['eventId'] = BaseInfo.event_id()
    data['hosts'] = []

    _hosts = dict(basic={}, cpu={}, memory={}, disks=[], os={}, ulimit={})
    _hosts['basic']['hostHash'] = HostInfo.host_ip_hash()
    _hosts['basic']['hostType'] = HostInfo.host_type()

    _hosts['cpu']['physicalCores'] = CpuInfo.cpu_physical_cores()
    _hosts['cpu']['logicalCores'] = CpuInfo.cpu_logical_cores()
    _hosts['cpu']['modelName'] = CpuInfo.cpu_model_name()
    _hosts['cpu']['frequency'] = CpuInfo.cpu_frequency()
    _hosts['cpu']['flags'] = CpuInfo.cpu_flags()

    _hosts['memory']['total'] = MemInfo.memory_total()
    _hosts['memory']['free'] = MemInfo.memory_free()
    _hosts['memory']['avaiable'] = MemInfo.memory_avaiable()

    _hosts['disks'] = DiskInfo.get_disks_info()

    _hosts['os']['os'] = OsInfo.os_name()
    _hosts['os']['version'] = OsInfo.os_release()

    _hosts['ulimit'] = MachineInfo.get_nofile()
    data['hosts'].append(_hosts)

    data['instances'] = []
    obd_info = {}
    obd_info['type'] = ObdInfo.obd_type()
    obd_info['version'] = ObdInfo.obd_version()
    obd_info['revision'] = ObdInfo.obd_revision()
    data['instances'].append(obd_info)
    return data


def telemetry_info_collect(plugin_context, *args, **kwargs):
    repositories = plugin_context.repositories
    repository = kwargs.get('target_repository')
    options = plugin_context.options
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    post_data = telemetry_machine_data()

    for repository in repositories:
        data = {}
        data['type'] = repository.name
        data['version'] = repository.version
        data['revision'] = repository.hash
        post_data['instances'].append(data)

    for component, _ in json.loads(getattr(options, 'data', {})).items():
        for plugin_name, _ in _.items():
            data = {}
            data['type'] = 'plugins'
            data['component'] = component
            data['name'] = plugin_name
            data['runTime'] = _['time']
            data['runResult'] = _['result']
            post_data['instances'].append(data)

    if repository.name in ['oceanbase', 'oceanbase-ce']:
        _ = cluster_config.get_global_conf()
        data = {}
        data['type'] = 'config'
        data['name'] = repository.name
        data['memoryLimit'] = _.get('memory_limit', '0') if _ else '0'
        data['cpuCount'] = _.get('cpu_count', '0') if _ else '0'
        data['syslogLevel'] = _.get('syslog_level', 'INFO') if _ else 'INFO'
        post_data['instances'].append(data)
    return plugin_context.return_true(post_data=json.dumps(post_data, indent=4))