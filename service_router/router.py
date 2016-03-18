# import asyncio
import logging
# import signal
# from functools import partial

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

	# def start(self):
	# 	for signame in ('SIGINT', 'SIGTERM'):
	# 		self.loop.add_signal_handler(getattr(signal, signame), partial(self._sig_handler, signame))
	#
	# 	asyncio.ensure_future(self._event_loop())
	# 	self.loop.run_forever()
	# 	self.loop.close()
	#
	# def _sig_handler(self, signame):
	# 	log.warning("Got %s: exiting" % (signame,))
	# 	self.loop.stop()
	#
	# async def _event_loop(self):
	# 	while True:
	# 		log.debug("Hello from event loop")
	# 		await asyncio.sleep(1)