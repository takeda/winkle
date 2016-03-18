from abc import abstractmethod, ABCMeta
from typing import Any, Callable, Dict, List

class AbsSourceSink(metaclass=ABCMeta):
	def __init__(self, config: Dict[str, Any]):
		self._hooks = None

	def set_hooks(self, hooks: Dict[str, Callable]):
		self._hooks = hooks

class AbsSource(AbsSourceSink):
	...

class AbsSink(AbsSourceSink):
	@abstractmethod
	def services_needed(self) -> Dict[str, List]:
		...
