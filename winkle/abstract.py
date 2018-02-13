from abc import abstractmethod, ABCMeta
from typing import Any, Callable, Dict, List, Optional, Tuple, Mapping

from .types import T_CHANGES, Node

T_SERVICES = Dict[str, List[str]]

class AbsSourceSink(metaclass=ABCMeta):
	def __init__(self, service_id: str, config: Mapping[str, Any]) -> None:
		self._service_id = service_id
		self._config = config
		self._hooks = None
		self._initialized = False

	def set_hooks(self, hooks: Mapping[str, Callable]):
		self._hooks = hooks


class AbsSource(AbsSourceSink):
	@abstractmethod
	def start(self) -> None:
		pass

	def services_needed(self) -> List[str]:
		assert self._hooks, 'set_hooks() was not called'
		return self._hooks['services_needed'](self._service_id)

	def change_detected(self, changes: T_CHANGES) -> None:
		assert self._hooks, 'set_hooks() was not called'
		return self._hooks['change_detected'](self._service_id, changes)

class AbsSink(AbsSourceSink):
	@abstractmethod
	def services_needed(self) -> T_SERVICES:
		pass

	@abstractmethod
	def process_update(self, source: str, changes: T_CHANGES) -> None:
		pass

	def service_nodes(self, service_name: str, data_center: Optional[str]) -> List[Node]:
		assert self._hooks, 'set_hooks() was not called'
		return self._hooks['service_nodes'](service_name, data_center)

	def service2source(self, canonical_service: str, data_center: Optional[str]) -> Tuple[str, str]:
		assert self._hooks, 'set_hooks() was not called'
		return self._hooks['service2source'](canonical_service, data_center)
