#! /usr/bin/env python
a = b'GhP$75mkLP&-215@S7"W"MM1=QTRatL\'ip_mb3i<^\'UXf)48N]X!GJ"O77GW3\'n%4[u5!cM\\pk+JaZ8rk2NYYI,!^ZMme*W@"Nqe$kTMo.ukq+/hZj/6#pndK\'!?NKQCE<+g^tr>e",OR*YtOXni*uRk=^'
import sys, zlib, base64
print('#! /usr/bin/env/python')
print('a = %s' % a)
sys.stdout.buffer.write(zlib.decompress(base64.a85decode(a)))
