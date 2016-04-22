import hashlib
import socket
from typing import Dict, FrozenSet, NamedTuple, Any

from .utils import hashabledict

Node = NamedTuple('Node', (
	('address', str),
	('port', str),
	('name', str),
	('attrs', hashabledict),
	('tags', FrozenSet[str])))

Changes = NamedTuple('Changes', (
	('added', FrozenSet[Node]),
	('removed', FrozenSet[Node]),
	('updated', FrozenSet[Node])))

T_CHANGES = Dict[str, Changes]

class NodeAddr:
	def __init__(self, node: Node):
		self.node = node

	def __hash__(self):
		return hash(self.node[0:2])

	def __eq__(self, other: Any):
		if not isinstance(other, self.__class__):
			return False

		return self.node[0:2] == other.node[0:2]

	def __getattribute__(self, item):
		if item == 'node':
			return object.__getattribute__(self, item)

		return self.node.__getattribute__(item)

	def __getitem__(self, item):
		return self.node.__getitem__(item)

	def __repr__(self):
		return self.node.__repr__()

sorting_salt = socket.getfqdn().encode('us-ascii', 'ignore')

def node_random_sort_key(node: Node) -> str:
	global sorting_salt

	# md5 is fast and evenly distributed, collision weakness has no impact in this use case
	digest = hashlib.md5()
	digest.update(sorting_salt)
	digest.update(('%s:%s' % (node[0], node[1])).encode('us-ascii', 'ignore'))

	return digest.hexdigest()
