from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from fastapi import Body
from enum import Enum

from service.model.deployments import Parameter
from service.model.components import ComponentInfo


class ComponentChangeMode(BaseModel):
    mode: str = Field(..., description="component change mode. eq 'scale_out', 'component_add'")


class BestComponentInfo(BaseModel):
    component_name: str = Field(..., description="component name, eq obporxy, ocp-express...")
    version: str = Field('', description="component version")
    deployed: int = Field(..., description="0 - not deployed, 1 - deployed")
    node: str = Field('', description="component node")
    component_info: Optional[List[ComponentInfo]] = Field([], description="component info")


class ComponentChangeInfo(BaseModel):
    component_list: List[BestComponentInfo] = Field(..., description="component list")


class Obproxy(BaseModel):
    component: str = Body(..., description='obproxy component name, ex:obproxy-ce,obproxy')
    version: str = Body(..., description='version')
    package_hash: str = Body('', description='obproxy package md5')
    release: str = Body(..., description='obproxy release no')
    prometheus_listen_port: int = Body(..., description='prometheus port')
    listen_port: int = Body(..., description='sql port')
    rpc_listen_port: int = Body(None, description='rpc port')
    obproxy_sys_password: str = Body('', description='obproxy_sys_password')
    parameters: List[Parameter] = Body(None, description='config parameter')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")
    cluster_name: str = Body('', description='cluster name')


class Obagent(BaseModel):
    component: str = Body(..., description='obagent component name, ex:obagent')
    version: str = Body(..., description='version')
    package_hash: str = Body('', description='obagent package md5')
    release: str = Body(..., description='obagent release no')
    monagent_http_port: int = Body(..., description='server port')
    mgragent_http_port: int = Body(..., description='debug port')
    http_basic_auth_password: str = Body('', description='http_basic_auth_password')
    parameters: List[Parameter] = Body(None, description='config parameter')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")


class Obconfigserver(BaseModel):
    component: str = Body(..., description='component name')
    version: str = Body(..., description='version')
    package_hash: str = Body('', description='package md5')
    release: str = Body(..., description='release no')
    parameters: List[Parameter] = Body(None, description='config parameter')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")
    listen_port: int = Body(..., description='server port')


class OcpExpress(BaseModel):
    component: str = Body(..., description='component name')
    version: str = Body(..., description='version')
    package_hash: str = Body('', description='package md5')
    release: str = Body(..., description='release no')
    port: int = Body(..., description='server port')
    admin_passwd: str = Body('', description='admin password')
    parameters: List[Parameter] = Body(None, description='config parameter')
    servers: List[str] = Body(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")


class ComponentChangeConfig(ComponentChangeMode):
    obproxy: Optional[Obproxy]
    obagent: Optional[Obagent]
    obconfigserver: Optional[Obconfigserver]
    ocpexpress: Optional[OcpExpress]
    home_path: str = Field(..., description="component change config path")


class ComponentChangeInfoDisplay(BaseModel):
    component_name: str = Field(..., description="component name")
    address: str = Field('', description="url address")
    username: str = Field('', description="username")
    password: str = Field('', description="password")
    access_string: str = Field('', description="access string")


class ComponentsChangeInfoDisplay(BaseModel):
    components_change_info: List[ComponentChangeInfoDisplay] = Field(..., description="components change info")


class ComponentServer(BaseModel):
    component_name: str = Field(..., description="component name")
    failed_servers: List[str] = Field(..., description="server ip, ex:[ '1.1.1.1','2.2.2.2']")


class ComponentLog(BaseModel):
    component_name: str = Field(..., description="component name")
    log: str = Field('', description="log path")


class ComponentsServer(BaseModel):
    components_server: List[ComponentServer] = Field(..., description="components server")


class ComponentDepends(BaseModel):
    component_name: str = Field(..., description="component name")
    depends: List[str] = Field([], description="depends component name")


class ConfigPath(BaseModel):
    config_path: str = Field(..., description="config path")