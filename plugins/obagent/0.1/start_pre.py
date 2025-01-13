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