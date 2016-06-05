import asyncio
import logging
import threading
from asyncio import CancelledError, ensure_future
from contextlib import closing
from typing import Any, Dict, List, Mapping, Optional, Tuple
from warnings import warn

from .abstract import AbsSource
# from .caching import async_ttl_cache
from .consul import Consul
from .errors import ConnectionError, HTTPResponseError
from .types import Node, NodeAddr, T_CHANGES, Changes
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

	@staticmethod
	def _get_monitor_services(services: List[str]) -> List[str]:
		monitors = []
		data_centers = set()

		for name in services:
			dc, _ = Consul.data_center(name)

			if dc in data_centers:
				continue

			monitors.append(name)
			data_centers.add(dc)

		return monitors

	async def _monitor(self) -> None:
		self._local.state = {}
		self._local.consul = self._consul(self._config['host'], self._config['port'],
			consistency=self._config['consistency'])

		# Services that we pay attention to
		services = self._hooks['services_needed']('consul')  # type: List[str]

		# Services which we use for monitoring (each supposed to have their own index)
		monitored_services = self._get_monitor_services(services)

		if len(monitored_services) == 0:
			log.error("No services to monitor")
			return

		log.debug("Using following services for monitoring indices: %s", ", ".join(monitored_services))

		# Schedule services
		pending = {ensure_future(self._health_service(service)) for service in monitored_services}
		index = {}  # type: Dict[str, str]
		while True:
			done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

			changed = False
			for task in done:
				try:
					i, service, _ = task.result()
				except CancelledError:
					log.info("Got cancellation request; exiting")
					raise

				if i == index.get(service, '0'):
					log.debug("%s - timeout; no change", service)
				else:
					changed = True
					index[service] = i

				pending.add(ensure_future(self._health_service(service, i)))

			if changed:
				log.debug("Calculating differences in consul changes %s", [(name, value) for name, value in index.items()])
				changes = await self._calculate_changes(services)
				self._hooks['change_detected']('consul', changes)
			else:
				log.debug("No changes detected")

		self._local.consul.close()

	@classmethod
	# @async_ttl_cache(60)
	async def _health_service(cls, service: str, index: str = None) -> Tuple[str, str, List[Node]]:
		while True:
			# noinspection PyBroadException
			try:
				index, response = await cls._local.consul.health.service(service, index, '5m', passing=True)
			except (ConnectionError, HTTPResponseError) as e:
				log.error('Received an error when querying consul: %r', e)
			except Exception:
				log.exception("Got an unknown exception when pulling information from consul")
			else:
				break

			log.info("%s: Sleeping for 1 minute before retrying" % service)
			await asyncio.sleep(60)

		nodes = []
		# noinspection PyUnboundLocalVariable
		for node in response:
			attrs, tags = hashabledict(), []

			if node['Service']['Tags']:
				for tag in node['Service']['Tags']:
					if '=' in tag:
						key, value = tag.split('=')
						attrs[key] = value
					else:
						tags.append(tag)

			node_name = '%s' % node['Node']['Node'].split('.')[0]

			nodes.append(Node(node['Service']['Address'], node['Service']['Port'], node_name, attrs, frozenset(tags)))

		return index, service, nodes

	@classmethod
	async def _get_new_state(cls, services: List[str]) -> Dict[str, List[Node]]:
		# schedule tasks
		futures = [asyncio.ensure_future(cls._health_service(service)) for service in services]

		# process results
		results = {}
		for future in asyncio.as_completed(futures):
			_, service, data = await future
			results[service] = data

		return results

	async def _calculate_changes(self, services: List[str]) -> T_CHANGES:
		old_state = self._local.state
		new_state = await self._get_new_state(services)

		# Calculate differences
		changes = {}
		for service in services:
			canonical_service = self._hooks['source2service']('consul', service)

			# get nodes for given service
			old_nodes = set(old_state.get(service, []))
			new_nodes = set(new_state.get(service, []))

			# list of nodes comparable by address/port
			old_addrs = set(map(NodeAddr, old_nodes))
			new_addrs = set(map(NodeAddr, new_nodes))

			added = frozenset(x.node for x in new_addrs - old_addrs)
			removed = frozenset(x.node for x in old_addrs - new_addrs)
			updated = frozenset(new_nodes - old_nodes - added)

			changes[canonical_service] = Changes(added, removed, updated)

		self._local.state = new_state

		return changes

	# thread safe interface
	def service_nodes(self, service: str, timeout: int = 5) -> List[Node]:
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
