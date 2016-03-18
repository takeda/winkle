from typing import Any, Dict, List

from .haproxy import HAProxy

class Sinks:
	def __init__(self, config: Dict[str, Any]):
		self.haproxy = HAProxy(config)

	def services_needed(self, source: str) -> List[str]:
		services = self.haproxy.services_needed()

		if source in services:
			return services[source]

		return []
