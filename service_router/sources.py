from typing import Any, Callable, Dict

from .consul import ConsulListener

class Sources:
	def __init__(self, config: Dict[str, Any]):
		self._hooks = None

		self.consul = ConsulListener(config)

	def set_hooks(self, hooks: Dict[str, Callable]):
		self._hooks = hooks

	def start(self):
		self.consul.start()

	def stop(self):
		self.consul.stop()
