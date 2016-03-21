from typing import Any, Callable, Dict

from .consul import ConsulListener

class Sources:
	def __init__(self, config: Dict[str, Any]):
		self.consul = ConsulListener(config)

	def set_hooks(self, hooks: Dict[str, Callable]):
		self.consul.set_hooks(hooks)

	def start(self):
		self.consul.start()
