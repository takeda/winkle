import asyncio
import logging
import threading
from asyncio import CancelledError
from contextlib import closing
from typing import Any, Dict, List, Mapping, Optional, Tuple
from warnings import warn

from service_router.errors import ConnectionError, HTTPResponseError
from .abstract import AbsSource
from .caching import async_ttl_cache
from .consul import Consul
from .node import Node, NodeAddr
from .utils import hashabledict

log = logging.getLogger(__name__)

class ConsulListener(AbsSource):
	_consul = Consul
	_local = threading.local()

	def __init__(self, config):
		super().__init__(config)

		self._loop = None           # type: Optional[asyncio.BaseEventLoop]
		self._listener_task = None  # type: Optional[threading.Thread]
		self.__control_lock = threading.Lock()

		self._config = config['sources']['consul']  # type: Mapping[str, Any]

	def start(self) -> None:
		assert self._hooks is not None

		def monitor_thread() -> None:
			"""Sets up current thread with its own asyncio event loop"""

			with closing(asyncio.new_event_loop()) as loop:  # type: asyncio.BaseEventLoop
				asyncio.set_event_loop(loop)
				loop.set_debug(True)

				with self.__control_lock:
					self._loop = loop

				loop.run_until_complete(self._monitor())

		with self.__control_lock:
			if self._listener_task:
				if self._listener_task.is_alive():
					warn("listener is already running", RuntimeWarning)
					return
				else:
					log.warning("listener was not running, restarting")

			self._listener_task = threading.Thread(target=monitor_thread, name='consul-monitor', daemon=True)
			self._listener_task.start()

	def stop(self):
		raise NotImplementedError()

	async def _monitor(self) -> None:
		self._local.state = {}

		services = self._hooks['services_needed']('consul')  # type: List[str]

		if len(services) == 0:
			log.error("No services to monitor")
			return

		service = services[0]
		log.debug("Starting monitoring of %s" % (service,))

		self._local.consul = self._consul(self._config['host'], self._config['port'],
			consistency=self._config['consistency'])

		index = None
		while True:
			try:
				i, _, _ = await self._health_service(service, index)
			except CancelledError:
				log.info("Got cancellation request; exiting")
				raise

			log.debug("%s: got index %s" % (service, i))

			if i == index:
				log.debug("%s - timeout; no change" % (service,))
				continue

			await self._detect_changes(services, i)
			index = i

		self._local.consul.close()

	@classmethod
	@async_ttl_cache(60)
	async def _health_service(cls, service: str, index: Optional[str] = None) -> Tuple[str, str, List[Node]]:
		while True:
			try:
				index, response = await cls._local.consul.health.service(service, index, '5m', passing=True)
			except (ConnectionError, HTTPResponseError) as e:
				log.error('Received an error when querying consul: %s', e)
			except Exception:
				log.exception("Got an unknown exception when pulling information from consul")
			else:
				break

			log.info("Sleeping for 1 minute before retrying")
			await asyncio.sleep(60)

		nodes = []
		for node in response:
			attrs, tags = hashabledict(), []

			if node['Service']['Tags']:
				for tag in node['Service']['Tags']:
					if '=' in tag:
						key, value = tag.split('=')
						attrs[key] = value
					else:
						tags.append(tag)

			nodes.append(Node(node['Service']['Address'], node['Service']['Port'],
			                  '%s_%s' % (node['Node']['Node'], node['Service']['Port']), attrs, tuple(tags)))

		return index, service, nodes

	@classmethod
	async def _get_new_state(cls, services: List[str], index: Optional[str] = None) -> Dict[str, List[Node]]:
		# schedule tasks
		futures = [asyncio.ensure_future(cls._health_service(service, index)) for service in services]

		# process results
		results = {}
		for future in asyncio.as_completed(futures):
			_, service, data = await future
			results[service] = data

		return results

	async def _detect_changes(self, services: List[str], index: str):
		log.debug("Detected change %s" % index)

		old_state = self._local.state
		new_state = await self._get_new_state(services)

		added, removed = {}, {}
		for service in services:
			log.debug("Processing service %s", service)

			old_nodes = old_state[service] if service in old_state else []
			new_nodes = new_state[service] if service in new_state else []

			old_addrs = set(map(NodeAddr, old_nodes))
			new_addrs = set(map(NodeAddr, new_nodes))
			added[service] = [x.node for x in new_addrs - old_addrs]
			removed[service] = [x.node for x in old_addrs - new_addrs]

		self._local.state = new_state
		self._hooks['change_detected']('consul', added, removed, [])

	# thread safe interface
	def service_nodes(self, service: str, timeout: Optional[int] = 5) -> List[Node]:
		"""
		Obtains list of available nodes for given service (threadsafe)
		:param service: name of the service (consul)
		:param timeout: how long to wait for response
		"""
		async def get_nodes_for_service():
			return self._local.state[service]

		with self.__control_lock:
			future = asyncio.run_coroutine_threadsafe(get_nodes_for_service(), self._loop)

		return future.result(timeout)
