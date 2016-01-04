import asyncio
import logging
import signal
from functools import partial

from .consul import ConsulListener

log = logging.getLogger(__name__)

class Router:
	def __init__(self, config):
		self.config = config

		self.loop = asyncio.get_event_loop()
		self.consul = ConsulListener(self.loop, {})

	def start(self):
		for signame in ('SIGINT', 'SIGTERM'):
			self.loop.add_signal_handler(getattr(signal, signame), partial(self._sig_handler, signame))

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

