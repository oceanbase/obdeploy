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
    obshell_port: int = Body(..., description='obshell port')


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
    vip_address: str = Body('', description='obproxy servers vip address')
    vip_port: str = Body('', description='obproxy servers vip port')
    dns: str = Body('', description='obproxy servers dns')


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

class Prometheus(BaseModel):
    component: str = Body('', description='prometheus component name,ex:prometheus')
    version: str = Body(..., description='version')
    release: str = Body(..., description='prometheus release no')
    parameters: List[Parameter] = Body(None, description='config parameter')
    home_path: str = Body('', description='install prometheus home path')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1']")
    port: int = Body(..., description='server port')
    basic_auth_users: dict = Body(..., description='auth user and password')

class Alertmanager(BaseModel):
    component: str = Body('', description='alertmanager component name,ex:alertmanager')
    version: str = Body(..., description='version')
    release: str = Body(..., description='alertmanager release no')
    parameters: List[Parameter] = Body(None, description='config parameter')
    home_path: str = Body('', description='install alertmanager home path')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1']")
    port: int = Body(..., description='server port')
    basic_auth_users: dict = Body(..., description='auth user and password')

class Grafana(BaseModel):
    component: str = Body('', description='grafana component name,ex:prometheus')
    version: str = Body(..., description='version')
    release: str = Body(..., description='grafana release no')
    parameters: List[Parameter] = Body(None, description='config parameter')
    home_path: str = Body('', description='install grafana home path')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1']")
    port: int = Body(..., description='server port')
    login_password: str = Body(..., description='login password')

class ComponentConfig(BaseModel):
    oceanbase: OceanBase
    obproxy: Optional[ObProxy]
    ocpexpress: Optional[OcpExpress]
    obagent: Optional[ObAgent]
    obclient: Optional[ObClient]
    obconfigserver: Optional[ObConfigserver]
    prometheus: Optional[Prometheus]
    grafana: Optional[Grafana]
    alertmanager: Optional[Alertmanager]


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
    
class ZoneInfo(BaseModel):
    name: str = Body('', description='zone name')
    ip: str = Body('', description='zone ip')
    status: str = Body('', description='zone status')

class ServerInfo(BaseModel):
    ip: str = Body('', description='server ip')
    sql_port: str = Body('', description='sql ip')
    rpc_port: str = Body('', description='rpc ip')
    zone: str = Body('', description='zone')
    status: str = Body('', description='server status')

class TenantInfo(BaseModel):
    id: str = Body('', description='tenant id')
    name: str = Body('', description='tenant name')
    type: str = Body('', description='tenant type')
    role: str = Body('', description='tenant role')
    mode: str = Body('', description='tenant mode')
    status: str = Body('', description='tenant status')

class DetialStats(BaseModel):
    active: int = Body(0, description='count of active instance')
    inactive: int = Body(0, description='count of inactive instance')
    other: int = Body(0, description='count of other status instance')
    total: int = Body(0, description='total count of instance')

class DeploymentDetial(BaseModel):
    name: str = Body('', description='deployment name')
    status: str = Body('', description='status, ex:CONFIGURED,DEPLOYED,STARTING,RUNNING,DESTROYED,UPGRADING')
    arch: str = Body('', description='deployment arch')
    version: str = Body('', description='deployment version')
    server_stats: DetialStats = Body(None, description='server statistics')
    tenant_stats: DetialStats = Body(None, description='tenant statistics')
    zone_info: List[ZoneInfo] = Body(None, description='zone info list')
    server_info: List[ServerInfo] = Body(None, description='server info list')
    tenant_info: List[TenantInfo] = Body(None, description='tenant info list')


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


class CreateTenantLog(BaseModel):
    log: str = Body('', description='create tenant log')
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


class OMSDeploymentStatus(StrEnum):
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


class TelemetryData(BaseModel):
    data: dict = Body(..., description='telemetry data')
    msg: str = Body('', description='telemetry message')


class CreateTenantConfig(BaseModel):
    tenant_name: str = Body('', description='tenant name')
    max_cpu: float = Body(None, description='max_cpu num')
    min_cpu: float = Body(None, description='min_cpu num')
    memory_size: str = Body(None, description='memory size')
    log_disk_size: str = Body(None, description='log disk size')
    mode: str = Body(..., description='tenant mode. {mysql, oracle}')
    charset: str = Body(..., description='database charset')
    variables: str = Body(..., description="Set the variables for the system tenant. [ob_tcp_invited_nodes='%'].")
    time_zone: str = Body(..., description='Tenant time zone. The default tenant time_zone is [+08:00].')
    collate: str = Body(..., description='Tenant collate.')
    optimize: str = Body('', description='Specify scenario optimization when creating a tenant, the default is consistent with the cluster dimension.\n{express_oltp, complex_oltp, olap, htap, kv}')
    password: str = Body(..., description='When creating a tenant, set password for user.')