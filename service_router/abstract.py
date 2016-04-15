from abc import abstractmethod, abstractproperty, ABCMeta
from typing import Any, Callable, Dict, List, Mapping

T_SERVICES = Dict[str, List[str]]

class AbsSourceSink(metaclass=ABCMeta):
	def __init__(self, config: Mapping[str, Any]):
		self._hooks = None
		self._initialized = False

	def set_hooks(self, hooks: Mapping[str, Callable]):
		self._hooks = hooks

class AbsSource(AbsSourceSink):
	@abstractmethod
	def start(self) -> None:
		...

class AbsSink(AbsSourceSink):
	@abstractproperty
	def services_needed(self) -> T_SERVICES:
		...

	@abstractmethod
	def process_update(self, source: str, added: Mapping[str, Any], removed: Mapping[str, Any],
			updated: Mapping[str, Any]) -> None:
		...
