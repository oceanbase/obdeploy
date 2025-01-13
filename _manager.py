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


from __future__ import absolute_import, division, print_function

import os
from tool import DirectoryUtil
from _stdio import SafeStdio


class Manager(SafeStdio):

    RELATIVE_PATH = ''

    def __init__(self, home_path, stdio=None):
        self.stdio = stdio
        self.path = os.path.join(home_path, self.RELATIVE_PATH)
        self.is_init = self._mkdir(self.path)

    def _mkdir(self, path):
        return DirectoryUtil.mkdir(path, stdio=self.stdio)

    def _rm(self, path):
        return DirectoryUtil.rm(path, self.stdio)
