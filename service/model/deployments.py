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

from enum import auto
from typing import List, Optional

from fastapi import Body
from pydantic import BaseModel
from fastapi_utils.enums import StrEnum

from service.common.task import TaskStatus, TaskResult
from service.model.tenant import TenantConfig
from service.model.database import DatabaseConnection


class Auth(BaseModel):
    user: str = Body('', description='ssh user')
    password: str = Body(None, description='ssh password')
    port: int = Body(22, description='ssh port')


class UserCheck(Auth):
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")


class PrecheckTaskResult(StrEnum):
    PASSED = auto()
    FAILED = auto()
    RUNNING = auto()


class DeployMode(StrEnum):
    DEMO = auto()
    PRODUCTION = auto()


class DeploymentStatus(StrEnum):
    INSTALLING = auto()
    DRAFT = auto()


class Resource(BaseModel):
    cpu: int = Body(None, description='cpu resource')
    memory: str = Body(None, description='memory resource')


class OceanbaseServers(BaseModel):
    ip: str = Body(..., description='server ip')
    parameters: dict = None


class Zone(BaseModel):
    name: str = Body(..., description='zone name')
    rootservice: str = Body(..., description='root service')
    servers: List[OceanbaseServers]


class Parameter(BaseModel):
    key: str = Body(..., description='parameter key')
    value: str = Body(..., description='parameter value')
    adaptive: bool = Body(None, description='parameter value is adaptive')


class OceanBase(BaseModel):
    component: str = Body(..., description='oceanbase component name,ex:oceanbase-ce,oceanbase')
    appname: str = Body(..., description='cluster name')
    version: str = Body(..., description='version')
    release: str = Body(..., description='oceanbase release no')
    package_hash: str = Body('', description='oceanbase package md5')
    mode: DeployMode = Body(..., description='deploy mode ex:DEMO,PRODUCTION')
    root_password: str = Body(..., description='root password')
    mysql_port: int = Body(..., description='sql port')
    rpc_port: int = Body(..., description='rpc port')
    home_path: str = Body('', description='install OceanBase home path')
    data_dir: str = Body('', description='OceanBase data path')
    redo_dir: str = Body('', description='clog path')
    parameters: List[Parameter] = Body(None, description='config parameter')
    topology: List[Zone] = Body(..., description='topology')


class ObProxy(BaseModel):
    component: str = Body(..., description='obproxy component name, ex:obproxy-ce,obproxy')
    version: str = Body(..., description='version')
    package_hash: str = Body('', description='obproxy package md5')
    release: str = Body(..., description='obproxy release no')
    cluster_name: str = Body(None, description='obproxy name')
    home_path: str = Body('', description='install obproxy home path')
    prometheus_listen_port: int = Body(..., description='prometheus port')
    rpc_listen_port: int = Body(None, description='rpc service port')
    listen_port: int = Body(..., description='sql port')
    parameters: List[Parameter] = Body(None, description='config parameter')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")


class OcpExpress(BaseModel):
    component: str = Body('ocp-express', description='ocp-express component name')
    version: str = Body(..., description='version')
    package_hash: str = Body('', description='ocp-express package md5')
    release: str = Body(..., description='ocp-express release no')
    home_path: str = Body('', description='install ocp-express home path')
    port: int = Body(..., description='server port')
    parameters: List[Parameter] = Body(None, description='config parameter')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")
    admin_passwd: str = Body(..., description="ocp-express admin password")


class ObAgent(BaseModel):
    component: str = Body('obagent', description='obagent component name,ex:obagent')
    version: str = Body(..., description='version')
    package_hash: str = Body('', description='obagent package md5')
    release: str = Body(..., description='obagent release no')
    home_path: str = Body('', description='install obagent home path')
    monagent_http_port: int = Body(..., description='server port')
    mgragent_http_port: int = Body(..., description='debug port')
    parameters: List[Parameter] = Body(None, description='config parameter')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")


class ObClient(BaseModel):
    component: str = Body('obclient', description='obclient component name,ex:obclient')
    version: str = Body(..., description='version')
    release: str = Body(..., description='obclient release no')
    parameters: List[Parameter] = Body(None, description='config parameter')
    home_path: str = Body('', description='install obclient home path')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")

class ObConfigserver(BaseModel):
    component: str = Body('ob-configserver', description='ob-configserver component name,ex:ob-configserver')
    version: str = Body(..., description='version')
    release: str = Body(..., description='ob-configserver release no')
    parameters: List[Parameter] = Body(None, description='config parameter')
    home_path: str = Body('', description='install ob-configserver home path')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")
    listen_port: int = Body(..., description='server port')

class ComponentConfig(BaseModel):
    oceanbase: OceanBase
    obproxy: Optional[ObProxy]
    ocpexpress: Optional[OcpExpress]
    obagent: Optional[ObAgent]
    obclient: Optional[ObClient]
    obconfigserver: Optional[ObConfigserver]


class DeploymentConfig(BaseModel):
    auth: Auth
    components: ComponentConfig
    home_path: str = Body('', description='global home path')


class DeploymentInfo(BaseModel):
    name: str = Body('', description='deployment name')
    config_path: str = Body('', description='config path')
    status: str = Body('',
                       description='ex:CONFIGURING,CONFIGURED,DEPLOYING,DEPLOYED,RUNNING,STOPPING,STOPPED,DESTROYING,DESTROYED,UPGRADING')
    config: DeploymentConfig = None


class RecoverAdvisement(BaseModel):
    description: str = Body('', description='advisement description')


class PreCheckInfo(BaseModel):
    name: str = Body(..., description='pre check item')
    server: str = Body(..., description='server node')
    status: TaskStatus = Body(TaskStatus.PENDING, description='status, ex:FINISHED, RUNNING, PENDING')
    result: PrecheckTaskResult = Body(PrecheckTaskResult.RUNNING, description='result, ex:PASSED, FAILED')
    recoverable: bool = Body(True, description='can be automatically repaired')
    code: str = Body('', description='error code')
    description: str = Body('', description='error description')
    advisement: RecoverAdvisement = Body(None, description='repaired suggestion')


class PreCheckResult(BaseModel):
    total: int = Body(0, description='total item for pre check')
    finished: int = Body(0, description='finished item for pre check')
    all_passed: bool = Body(False, description='is all passed')
    status: TaskResult = Body(TaskResult.RUNNING, description='pre check task status,ex:RUNNING,SUCCESSFUL,FAILED')
    message: str = Body('', description='pre check task message')
    info: List[PreCheckInfo] = Body(None, description='pre check item info')


class RecoverChangeParameter(BaseModel):
    name: str = Body(..., description='repaired item')
    old_value: object = Body('', description='old value item')
    new_value: object = Body('', description='new value item')


class ComponentInfo(BaseModel):
    component: str = Body(..., description='install component name')
    status: TaskStatus = Body(..., description='status, ex:FINISHED, RUNNING, PENDING')
    result: TaskResult = Body(..., description='result, ex:SUCCESSFUL, FAILED')


class TaskInfo(BaseModel):
    total: int = Body(0, description='total item for install')
    finished: int = Body(0, description='finished item for install')
    current: str = Body('', description='current item for install')
    status: TaskResult = Body(..., description='status,ex:RUNNING,SUCCESSFUL,FAILED')
    msg: str = Body('', description='task message')
    info: List[ComponentInfo] = Body(None, description='install item info')


class ConnectionInfo(BaseModel):
    component: str = Body(..., description='component name')
    access_url: str = Body(..., description='access url')
    user: str = Body(..., description='user')
    password: str = Body(..., description='password')
    connect_url: str = Body(..., description='connect url')


class InstallLog(BaseModel):
    log: str = Body('', description='install log')
    offset: int = Body(0, description='log offset')


class Deployment(BaseModel):
    name: str = Body(..., description='deployment name')
    status: str = Body(..., description='status, ex:CONFIGURED,DEPLOYED,STARTING,RUNNING,DESTROYED,UPGRADING')


class DeploymentReport(BaseModel):
    name: str = Body(..., description='component name')
    version: str = Body(..., description='component version')
    servers: List[str] = Body(..., description='server ip')
    status: TaskResult = Body(..., description='status, ex: RUNNING, SUCCESSFUL, FAILED')


class DeployConfig(BaseModel):
    name: str
    config: str

    class Config:
        orm_mode = True


class OCPDeploymentStatus(StrEnum):
    INIT = auto()
    DEPLOYING = auto()
    FINISHED = auto()


class ClusterManageInfo(BaseModel):
    machine: Optional[int] = Body(None, description='manage machine num')


class OcpServer(BaseModel):
    component: str = Body('ocp-server', description='ocp-server component name')
    version: str = Body('', description='version')
    package_hash: str = Body('', description='ocp-server package md5')
    release: str = Body('', description='ocp-server release no')
    home_path: str = Body('', description='install ocp-server home path')
    soft_dir: str = Body('', description='software path')
    log_dir: str = Body('', description='log dir')
    ocp_site_url: str = Body('', description='ocp server url')
    port: int = Body(..., description='server port')
    admin_password: str = Body(..., description='admin password')
    parameters: List[Parameter] = Body(None, description='config parameter')
    memory_size: str = Body('2G', description='ocp server memory size')
    ocp_cpu: int = Body(0, description='ocp server cpu num')
    meta_tenant: Optional[TenantConfig] = Body(None, description="meta tenant config")
    monitor_tenant: Optional[TenantConfig] = Body(None, description="monitor tenant config")
    manage_info: Optional[ClusterManageInfo] = Body(None, description='manage cluster info')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")
    metadb: Optional[DatabaseConnection] = Body(None, description="connection info of metadb")


class OcpComponentConfig(BaseModel):
    oceanbase: Optional[OceanBase]
    obproxy: Optional[ObProxy]
    ocpserver: OcpServer


class OCPDeploymnetConfig(BaseModel):
    auth: Auth
    components: OcpComponentConfig
    home_path: str = Body('', description='global home path')
    launch_user: Optional[str] = Body(None, description='process user')


class ScenarioType(BaseModel):
    type: str = Body(..., description='scenario name')
    desc: str = Body(..., description='scenario description')
    value: str = Body(..., description='scenario value')

