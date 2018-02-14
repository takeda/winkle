from typing import Dict, FrozenSet, NamedTuple, Any

class hashabledict(dict):
	def __hash__(self) -> int:
		return hash(tuple(sorted(self.items())))

	def __eq__(self, other: Dict) -> bool:
		if not isinstance(other, self.__class__):
			return False

		return tuple(sorted(self.items())) == tuple(sorted(other.items()))

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
	"""
	Wrapper for `Node` which makes it comparable only by address/port
	"""

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

