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
