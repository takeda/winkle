import logging

from .sources import Sources
from .sinks import Sinks

log = logging.getLogger(__name__)

class Router:
	def __init__(self, config):
		self.config = config

		self.sources = Sources(config)
		self.sinks = Sinks(config)

		hooks = {
			'services_needed': self.sinks.services_needed
		}
		self.sources.set_hooks(hooks)

	def start(self):
		self.sources.start()
