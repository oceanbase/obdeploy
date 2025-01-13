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
from service.handler.component_handler import ComponentHandler
from service.handler.deployment_handler import DeploymentHandler
from service.handler.service_info_handler import ServiceInfoHandler
from service.handler.comment_handler import CommonHandler
from service.handler.mirror_handler import MirrorHandler
from service.handler.ocp_handler import OcpHandler
from service.handler.metadb_handler import MetadbHandler
from service.handler.component_change_handler import ComponentChangeHandler
from service.handler.rsa_handler import RSAHandler


def new_component_handler():
    return ComponentHandler()


def new_deployment_handler():
    return DeploymentHandler()


def new_common_handler():
    return CommonHandler()


def new_service_info_handler():
    return ServiceInfoHandler()


def new_mirror_handler():
    return MirrorHandler()


def new_ocp_handler():
    return OcpHandler()


def new_metadb_handler():
    return MetadbHandler()


def new_server_info_handler():
    return ServiceInfoHandler()


def new_component_change_handler():
    return ComponentChangeHandler()
def new_rsa_handler():
    return RSAHandler()
