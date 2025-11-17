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

from typing import List, Optional, Union
from enum import auto
from fastapi import Body
from fastapi_utils.enums import StrEnum
from pydantic import BaseModel

from service.model.ssh import SshAuth
from service.model.parameter import Parameter
from service.model.deployments import OCPDeploymentStatus
from service.model.tenant import TenantConfig
from service.model.resource import ServerResource
from service.model.task import TaskStatus, TaskResult
from service.model.database import DatabaseConnection
from service.model.backup import BackupMethod


class OmsImages(BaseModel):
    oms_image: List[str] = Body(..., description="Oms images")


class OmsDeploymentConfig(BaseModel):
    auth: SshAuth = Body(..., description="ssh auth info")
    image: str = Body(..., description="image name")
    servers: str = Body(..., description="oms nodes ips")
    mount_path: str = Body(..., description="oms mount path")
    drc_cm_db: str = Body('oms_cm', description="cm db name")
    drc_rm_db: str = Body('oms_rm', description="cm db name")
    oms_meta_host: str = Body(..., description="meta db host")
    oms_meta_port: int = Body(2881, description="meta db port")
    oms_meta_user: str = Body('root', description="user")
    oms_meta_password: str = Body('', description="meta db password")
    tsdb_password: str = Body(None, description="influxdb password")
    tsdb_service: str = Body(None, description="influxdb service")
    tsdb_url: str = Body(None, description="influxdb url")
    tsdb_username: str = Body(None, description="influxdb username")
    apsara_audit_sls_access_key: str = Body(None, description="sls key")
    apsara_audit_sls_access_secret: str = Body(None, description="sls secret")
    apsara_audit_sls_endpoint: str = Body(None, description="sls endpoint")
    apsara_audit_sls_ops_site_topic: str = Body(None, description="sls ops site topic")
    apsara_audit_sls_user_site_topic: str = Body(None, description="sls user site topic")
    ghana_server_port: int = Body(8090, description="ghana server port")
    nginx_server_port: int = Body(8089, description="nginx server port")
    cm_server_port: int = Body(8088, description="cm server port")
    supervisor_server_port: int = Body(9000, description="supervisor server port")
    sshd_server_port: int = Body(2023, description="sshd server port")
    regions: List = Body(..., description="regions")





