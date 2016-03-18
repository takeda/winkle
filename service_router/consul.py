import asyncio
import logging
import threading
from asyncio import ensure_future, CancelledError
from typing import Any, Dict, List, Tuple
from warnings import warn

from consul.aio import Consul

from .abstract import AbsSource

log = logging.getLogger(__name__)

class ConsulListener(AbsSource):
	def __init__(self, config: Dict[str, Any]):
		super().__init__(config)

		self._listener_task = None  # type: threading.Thread
		self._listener_stop = None  # type: threading.Event
		self.__control_lock = threading.Lock()

		self.services = []  # type: List[str]

		self._config = config['sources']['consul']  # type: Dict[str, Any]
		self._consul = Consul

	def start(self) -> None:
		with self.__control_lock:
			if self._listener_task:
				if self._listener_task.is_alive():
					warn("listener is already running", RuntimeWarning)
					return
				else:
					log.warning("listener was not running, restarting")

			self.services = self._hooks['services_needed']('consul')

			if len(self.services) == 0:
				log.error("No services configured to monitor")
				return

			self._listener_task = threading.Thread(target=self._monitor_thread, name='consul-monitor', daemon=True)
			self._listener_stop = threading.event()
			self._listener_task.start()

	def wait(self) -> None:
		self._listener_task.join()

	def stop(self) -> None:
		with self.__control_lock:
			if not self._listener_task:
				warn("issued stop, but there is no listener task", RuntimeWarning)
				return

			self._listener_stop.set()
			self._listener_task = None

	def _monitor_thread(self) -> None:
		with asyncio.get_event_loop() as loop:  # type: asyncio.BaseEventLoop
			loop.run_until_complete(self._monitor())

	async def _monitor(self) -> None:
		consul = self._consul(self._config['host'], self._config['port'], consistency = self._config['consistency'])

		if len(self.services) == 0:
			log.error("No services to monitor")
			return

		service = self.services[0]
		log.debug("Starting monitoring of %s" % (service,))

		index = None
		while True:
			try:
				i, response = await self._health_service(consul, service, index)  # type: Tuple[str, Any]
			except CancelledError:
				log.info("Got cancellation request; exiting")
				raise

			log.debug("%s: got index %s" % (service, i))

			if i == index:
				log.debug("%s - timeout; no change" % (service,))
				continue

			self._detect_changes(i)
			index = i

#	@async_ttl_cache(60)
	@staticmethod
	async def _health_service(consul: Consul, service: str, index: str = None) -> Tuple[str, List[Dict]]:
		index, response = await consul.health.service(service, index, '5s', passing=True)

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

	def _detect_changes(self, index: str):
		log.debug("Detected change %d" % index)

		for service in self.services:
			pass