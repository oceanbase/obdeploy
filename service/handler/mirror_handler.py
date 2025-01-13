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

