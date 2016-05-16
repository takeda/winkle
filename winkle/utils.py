import collections
from typing import Dict

class hashabledict(dict):
	def __hash__(self) -> int:
		return hash(tuple(sorted(self.items())))

	def __eq__(self, other: Dict) -> bool:
		if not isinstance(other, self.__class__):
			return False

		return tuple(sorted(self.items())) == tuple(sorted(other.items()))

def mergedict(d1, d2):
	for key, new in d2.items():
		old = d1.get(key)
		if isinstance(old, collections.Mapping) and isinstance(new, collections.Mapping):
			mergedict(old, new)
		else:
			d1[key] = new
