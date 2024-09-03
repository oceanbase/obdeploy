
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
