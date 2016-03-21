import asyncio
import logging
import threading
from asyncio import CancelledError
from contextlib import closing
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Set, Iterable, NamedTuple
from warnings import warn

from consul.aio import Consul

from .abstract import AbsSource
from .caching import async_ttl_cache

class hashabledict(dict):
	def __hash__(self) -> int:
		return hash(tuple(sorted(self.items())))

	def __eq__(self, other: Dict) -> bool:
		if not isinstance(other, self.__class__):
			return False

		return tuple(sorted(self.items())) == tuple(sorted(other.items()))

Node = NamedTuple('Node', (('address', str), ('port', str), ('attrs', Optional[hashabledict]), ('tags', Optional[Tuple[str]])))

class NodeAddr:
	def __init__(self, node: Node):
		self.node = node

	def __hash__(self):
		return hash(self.node[0:2])

	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False

		return self.node[0:2] == other.node[0:2]

	def __getattribute__(self, item):
		if item == 'node':
			return object.__getattribute__(self, item)

		return self.node.__getattribute__(item)

	def __getitem__(self, item):
		return self.node.__getitem__(item)

	def __repr__(self):
		return self.node.__repr__()

log = logging.getLogger(__name__)

class ConsulListener(AbsSource):
	_consul = Consul
	_local = threading.local()

	def __init__(self, config):
		super().__init__(config)

		self._listener_task = None  # type: Optional[threading.Thread]
		self.__control_lock = threading.Lock()

		self._config = config['sources']['consul']  # type: Mapping[str, Any]

	def start(self) -> None:
		assert self._hooks is not None

		with self.__control_lock:
			if self._listener_task:
				if self._listener_task.is_alive():
					warn("listener is already running", RuntimeWarning)
					return
				else:
					log.warning("listener was not running, restarting")

			self._listener_task = threading.Thread(target=self._monitor_thread, name='consul-monitor', daemon=False)
			self._listener_task.start()

	def _monitor_thread(self) -> None:
		with closing(asyncio.new_event_loop()) as loop:  # type: asyncio.BaseEventLoop
			asyncio.set_event_loop(loop)
			loop.set_debug(True)
			loop.run_until_complete(self._monitor())

	async def _monitor(self) -> None:
		self._local.state = {}
		self._local.consul = self._consul(self._config['host'], self._config['port'],
		                                  consistency=self._config['consistency'])

		services = self._hooks['services_needed']('consul')  # type: List[str]

		if len(services) == 0:
			log.error("No services to monitor")
			return

		service = services[0]
		log.debug("Starting monitoring of %s" % (service,))

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

	@classmethod
	@async_ttl_cache(60)
	async def _health_service(cls, service: str, index: Optional[str] = None) -> Tuple[str, str, List[Node]]:
		index, response = await cls._local.consul.health.service(service, index, '300s', passing=True)

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

			nodes.append(Node(node['Service']['Address'], node['Service']['Port'], attrs, tuple(tags)))

		return index, service, nodes

	@classmethod
	async def _get_new_state(cls, services: List[str], index: Optional[str] = None) -> Dict[str, List[Node]]:
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

		for service in services:
			log.debug("Processing service %s", service)

			old_nodes = old_state[service] if service in old_state else []
			new_nodes = new_state[service] if service in new_state else []

			old_addrs = set(map(NodeAddr, old_nodes))
			new_addrs = set(map(NodeAddr, new_nodes))
			added = [x.node for x in new_addrs - old_addrs]
			removed = [x.node for x in old_addrs - new_addrs]

			print(added)
			print(removed)

		#self._local.state = new_state