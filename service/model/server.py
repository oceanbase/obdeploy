from fastapi import Body
from fastapi_utils.enums import StrEnum
from typing import List, Optional
from pydantic import BaseModel
from enum import auto

from service.model.metadb import DatabaseConnection


class InstallerMode(StrEnum):
    STANDARD = auto()
    COMPACT = auto()


class ComponentInfo(BaseModel):
    name: str = Body("ocp-server", description="ocp component")
    ip: List[str] = Body([], description="server address")


class OcpServerInfo(BaseModel):
    user: str = Body('', description="deploy user")
    ocp_version: str = Body('', description="ocp-server current version")
    component: List[ComponentInfo] = Body([], description="component info")
    tips: bool = Body(False, description='display tips')
    msg: str = Body('', description="failed message")


class MsgInfo(BaseModel):
    msg: str = Body(..., description="failed message")
    status: int = Body(..., description='eq: 0, 1')


class UserInfo(BaseModel):
    username: str = Body(..., description='system user')


