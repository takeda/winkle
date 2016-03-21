from abc import abstractmethod, ABCMeta
from typing import Any, Callable, Dict, List, Mapping

class AbsSourceSink(metaclass=ABCMeta):
	def __init__(self, config: Mapping[str, Any]):
		self._hooks = None

	def set_hooks(self, hooks: Dict[str, Callable]):
		self._hooks = hooks

class AbsSource(AbsSourceSink):
	@abstractmethod
	def start(self) -> None:
		...

class AbsSink(AbsSourceSink):
	@abstractmethod
	def services_needed(self) -> Dict[str, List]:
		...

	@abstractmethod
	def process_update(self, changes: Mapping[str, Any]) -> None:
		...
