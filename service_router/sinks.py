import logging
from typing import Any, Callable, List, Optional, Mapping

from .haproxy import HAProxy

log = logging.getLogger(__name__)

class Sinks:
	def __init__(self, config: Mapping[str, Any], services: Mapping[str, Any]):
		self._hooks = None  # type: Optional[Mapping[str, Callable]]
		self.haproxy = HAProxy(config, services)

	def set_hooks(self, hooks: Mapping[str, Callable]) -> None:
		self._hooks = hooks
		self.haproxy.set_hooks(hooks)

	def start(self):
		self.haproxy.start()

	def stop(self):
		pass

	def services_needed(self, source: str) -> List[str]:
		"""Returns list of services for given source
		:param source name of the source (ex. consul)
		:returns list of service names"""

		services = self.haproxy.services_needed

		return services.get(source, [])

	def change_detected(self, source, added, removed, updated):
		def process_change():
			log.debug("Got change from %s", source)
			self.haproxy.process_update(source, added, removed, updated)

		self._hooks['run_main_thread'](process_change)
