import asyncio
import functools
import logging
import signal

from .consul import Consul

log = logging.getLogger(__name__)

class Router:
	def __init__(self):
		self.loop = asyncio.get_event_loop()
		self.consul = Consul(self.loop, {})

	def start(self):
		for signame in ('SIGINT', 'SIGTERM'):
			self.loop.add_signal_handler(getattr(signal, signame), functools.partial(self._sig_handler, signame))

		asyncio.ensure_future(self._event_loop())
		self.loop.run_forever()
		self.loop.close()

	def _sig_handler(self, signame):
		log.warning("Got %s: exiting" % (signame,))
		self.loop.stop()

	async def _event_loop(self):
		while True:
			log.debug("Hello from event loop")
			await asyncio.sleep(1)

