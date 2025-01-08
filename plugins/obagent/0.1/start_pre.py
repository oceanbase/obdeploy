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

from __future__ import absolute_import, division, print_function

import sys
import random
import base64

from Crypto import Random
from Crypto.Cipher import AES


if sys.version_info.major == 2:

    def generate_key(key):
        genKey = [chr(0)] * 16
        for i in range(min(16, len(key))):
            genKey[i] = key[i]
        i = 16
        while i < len(key):
            j = 0
            while j < 16 and i < len(key):
                genKey[j] = chr(ord(genKey[j]) ^ ord(key[i]))
                j, i = j+1, i+1
        return "".join(genKey)

    class AESCipher:
        bs = AES.block_size

        def __init__(self, key):
            self.key = generate_key(key)

        def encrypt(self, message):
            message = self._pad(message)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return base64.b64encode(iv + cipher.encrypt(message)).decode('utf-8')

        def _pad(self, s):
            return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

else:
    def generate_key(key):
        genKey = [0] * 16
        for i in range(min(16, len(key))):
            genKey[i] = key[i]
        i = 16
        while i < len(key):
            j = 0
            while j < 16 and i < len(key):
                genKey[j] = genKey[j] ^ key[i]
                j, i = j+1, i+1
        genKey = [chr(k) for k in genKey]
        return bytes("".join(genKey), encoding="utf-8")

    class AESCipher:
        bs = AES.block_size

        def __init__(self, key):
            self.key = generate_key(key)

        def encrypt(self, message):
            message = self._pad(message)
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return str(base64.b64encode(iv + cipher.encrypt(bytes(message, encoding='utf-8'))), encoding="utf-8")

        def _pad(self, s):
            return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)


def encrypt(key, data):
    key = base64.b64decode(key)
    cipher = AESCipher(key)
    return cipher.encrypt(data)


def generate_aes_b64_key():
    n = random.randint(1, 3) * 8
    key = []
    c = 0
    while c < n:
        key += chr(random.randint(33, 127))
        c += 1
    key = ''.join(key)
    return base64.b64encode(key.encode('utf-8'))


def start_pre(plugin_context, *args, **kwargs):
    plugin_context.set_variable('generate_key', generate_key)
    plugin_context.set_variable('AESCipher', AESCipher)
    plugin_context.set_variable('encrypt', encrypt)
    plugin_context.set_variable('generate_aes_b64_key', generate_aes_b64_key)
    return plugin_context.return_true()