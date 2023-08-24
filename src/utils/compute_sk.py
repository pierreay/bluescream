#!/usr/bin/env python3

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

# * Encryption

k = "b4c8667a965538edbaf06f8de70be536"
k = int(k, 16)
p = 111604163534833395158929986929630000560
# k and p are int now.

key = b''
for i in range(0, 16):
    k_i = (k >> 128 - (8 * (i+1))) & 0xFF
    key = key + k_i.to_bytes()

pt = b''
for i in range(0, 16):
    p_i = (p >> 128 - (8 * (i+1))) & 0xFF
    pt = pt + p_i.to_bytes()

import ipdb; ipdb.set_trace()

cipher = AES.new(key, AES.MODE_ECB)
ciphertext = cipher.encrypt(pt)
print(ciphertext)
