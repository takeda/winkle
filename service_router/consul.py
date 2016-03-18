import asyncio
import logging
from asyncio import ensure_future, CancelledError
from typing import Any, Dict
from warnings import warn

from consul.aio import Consul

from .abstract import AbsSource

log = logging.getLogger(__name__)

class ConsulListener(AbsSource):
	def __init__(self, config: Dict[str, Any]):
		super().__init__()

		self._tasks = {}
		self.services = []

		self._config = config['sources']['consul']  # type: Dict[str, Any]
		self._consul = Consul(self._config['host'], self._config['port'], consistency = self._config['consistency'])

	def start(self) -> None:
		if 'listener' in self._tasks:
			if self._tasks['listener'].done():
				log.warning("listener was not running, restarting")
			else:
				warn("listener is already running", RuntimeWarning)
				return

		self.services = self._hooks['get_services']('consul')

		if len(self.services) == 0:
			log.error("No services configured to monitor")
			return

		self._tasks['listener'] = ensure_future(self._monitor())

	def wait(self) -> None:
		if 'listener' not in self._tasks:
			warn("issued wait, but there is no listener task", RuntimeWarning)
			return

		self.loop.run_until_complete(asyncio.wait(self._tasks.values()))

	def stop(self) -> None:
		if 'listener' not in self._tasks:
			warn("issued stop, but there is no listener task", RuntimeWarning)
			return

		self._tasks['listener'].cancel()
		del self._tasks['listener']

	async def _monitor(self) -> None:
		service = self.services[0]

		log.debug("Starting monitoring of %s" % (service,))

		index = None
		while True:
			try:
				i, response = await self._health_service(service, index)
			except CancelledError:
				log.info("Got cancellation request; exiting")
				raise

			print("%s: got index %s" % (service, i))

			if i == index:
				log.debug("%s - timeout; no change" % (service,))
				continue

			self.callback(response)
			index = i

#	@async_ttl_cache(60)
	async def _health_service(self, service, index = None):
		index, response = await self.consul.health.service(service, index, '5s', passing = True)

		services = []
		for node in response:
			attrs, tags = {}, []
			for tag in node['Service']['Tags']:
				if '=' in tag:
					key, value = tag.split('=')
					attrs[key] = value
				else:
					tags.append(tag)

			services.append({
				'address': node['Service']['Address'],
				'port': node['Service']['Port'],
				'attrs': attrs,
				'tags': tags
			})

		return index, services

	def callback(self, response):
		print("Callback: %r" % response)
