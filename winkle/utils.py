from typing import Dict

class hashabledict(dict):
	def __hash__(self) -> int:
		return hash(tuple(sorted(self.items())))

	def __eq__(self, other: Dict) -> bool:
		if not isinstance(other, self.__class__):
			return False

		return tuple(sorted(self.items())) == tuple(sorted(other.items()))
