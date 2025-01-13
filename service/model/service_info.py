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
from fastapi import Body
from pydantic import BaseModel
from typing import List


class ServiceInfo(BaseModel):
    user: str = Body(..., description='user name')


class DeployName(BaseModel):
    name: str = Body('', description="deploy name list")
    deploy_user: str = Body('', description="deploy user")
    ob_servers: List[str] = Body([], description="ob servers")
    ob_version: str = Body('', description="ob version")
    create_date: str = Body(None, description="ob create date")


class DeployNames(BaseModel):
    name: List[str] = Body([], description="deploy name list")
