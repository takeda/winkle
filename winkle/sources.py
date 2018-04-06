from typing import Any, Callable, List, Mapping, Optional

from .consul_listener import ConsulListener
from .types import Node

class Sources:
	def __init__(self, config: Mapping[str, Any]):
		self._hooks = None
		self.consul = ConsulListener(config)

	def set_hooks(self, hooks: Mapping[str, Callable]):
		self._hooks = hooks
		self.consul.set_hooks(hooks)

	def start(self):
		self.consul.start()

	def stop(self):
		pass

	def service_nodes(self, service_name: str, data_centers: Optional[str]) -> List[Node]:
		source, services = self._hooks['service2sources'](service_name, data_centers)
		if source == 'consul':
			return [ n for service in services for n in self.consul.service_nodes(service) ]

		raise NotImplemented()
