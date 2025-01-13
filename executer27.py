
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

import os
import sys
import new
import time
import logging
import getopt
import json
import string
import random
import datetime
import decimal
import ConfigParser
import socket
import platform
import ctypes
import mmap

if __name__ == '__main__':
    defaultencoding = 'utf-8'
    if sys.getdefaultencoding() != defaultencoding:
        try:
            from imp import reload
        except:
            pass
        reload(sys)
        sys.setdefaultencoding(defaultencoding)

    OBD_INSTALL_PRE = os.environ.get('OBD_INSTALL_PRE', '/')
    sys.path.append(os.path.join(OBD_INSTALL_PRE, 'usr/obd/lib/executer/executer27/site-packages'))
    del sys.argv[0]
    sys.path.append(os.path.dirname(sys.argv[0]))
    execfile(sys.argv[0])
