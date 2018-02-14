import collections
import hashlib
import socket
import struct

from .types import Node

SORTING_SALT = socket.getfqdn().encode('us-ascii', 'ignore')

def mergedict(d1, d2):
	for key, new in d2.items():
		old = d1.get(key)
		if isinstance(old, collections.Mapping) and isinstance(new, collections.Mapping):
			mergedict(old, new)
		else:
			d1[key] = new

def node_random_sort_key(node: Node) -> str:
	global SORTING_SALT

	# md5 is fast and evenly distributed, collision weakness has no impact in this use case
	digest = hashlib.md5()
	digest.update(SORTING_SALT)
	digest.update(('%s:%s' % (node[0], node[1])).encode('us-ascii', 'ignore'))

	return digest.hexdigest()

def node_server_id(node: Node) -> int:
	digest = hashlib.md5()
	digest.update(('%s:%s' % (node[0], node[1])).encode('us-ascii', 'ignore'))

	# haproxy expects signed 32 bit integer > 0
	return abs(struct.unpack('@i', digest.digest()[:4])[0]) or 1
