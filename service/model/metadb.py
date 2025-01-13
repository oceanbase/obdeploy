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
from typing import List, Optional
from enum import auto, Enum
from fastapi import Body
from fastapi_utils.enums import StrEnum
from pydantic import BaseModel

from service.model.ssh import SshAuth
from service.model.database import DatabaseConnection
from service.model.parameter import Parameter
from service.model.deployments import OCPDeploymentStatus


class PrecheckTaskResult(StrEnum):
    PASSED = auto()
    FAILED = auto()
    RUNNING = auto()


class Flag(Enum):
    not_matched = 0
    same_disk = 1
    data_and_log_same_disk = 2
    home_data_or_home_log_same_disk = 3
    data_log_different_disk = 4


class MetadbDeploymentConfig(BaseModel):
    auth: SshAuth = Body(None, description="ssh auth info")
    cluster_name: str = Body("obcluster", description="cluster name")
    servers: List[str] = Body(..., description = "servers to deploy")
    root_password: str = Body("", description="password of user root@sys")
    home_path: str = Body("", description="home path to install")
    data_dir: Optional[str] = Body("", description="data directory")
    log_dir: Optional[str] = Body("", description="log directory")
    sql_port: int = Body(2881, description="sql port")
    rpc_port: int = Body(2882, description="rpc port")
    devname: str = Body('', description='devname')
    parameters: Optional[List[Parameter]] = Body(None, description='config parameter')


class MetadbDeploymentInfo(BaseModel):
    id: int = Body(0, description="metadb deployment id")
    status: OCPDeploymentStatus = Body(OCPDeploymentStatus.INIT, description="metadb deployment status, ex: INIT, FINISHED")
    config: MetadbDeploymentConfig = Body(None, description="metadb deployment")
    connection: Optional[DatabaseConnection] = Body(None, description="connection info of metadb")


class RecoverChangeParameter(BaseModel):
    name: str = Body(..., description='repaired item')
    old_value: str = Body(None, description='old value item')
    new_value: str = Body(None, description='new value item')
