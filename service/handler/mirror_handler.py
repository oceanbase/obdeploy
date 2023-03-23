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

from _errno import LockError
from service.common import log
from service.common import const
from service.handler.base_handler import BaseHandler
from singleton_decorator import singleton
from service.model.mirror import Mirror

@singleton
class MirrorHandler(BaseHandler):

    def list_mirrors(self):
        if self.context['mirror']['remote_mirror_info_status'] != const.FINISHED:
            raise Exception('update mirror not finished')
        remote_mirror_info = self.context['mirror']['remote_mirror_info']
        return remote_mirror_info

    async def init_mirrors_info(self):
        self.context['mirror']['remote_mirror_info_status'] = const.RUNNING
        try:
            mirror_list = []
            mirrors = self.obd.mirror_manager.get_remote_mirrors(is_enabled=True)
            mirrors_disabled = self.obd.mirror_manager.get_remote_mirrors(is_enabled=False)
            mirrors.extend(mirrors_disabled)
            for mirror in mirrors:
                mirror_list.append(
                    Mirror(name=mirror.name, mirror_path=mirror.mirror_path, section_name=mirror.section_name,
                        baseurl=mirror.baseurl,
                        repomd_age=mirror.repomd_age, priority=mirror.priority, gpgcheck=mirror.gpgcheck,
                        enabled=mirror.enabled, available=mirror.available, repo_age=mirror.repo_age))
            self.context['mirror']['remote_mirror_info'] = mirror_list
        except LockError:
            log.get_logger().error('Another app is currently holding the obd lock.')
        except Exception as ex:
            log.get_logger().exception("got exception {} when init mirror".format(ex))
        finally:
            self.context['mirror']['remote_mirror_info_status'] = const.FINISHED

