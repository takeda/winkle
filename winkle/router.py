import asyncio
import functools
import logging
import signal
import threading
from contextlib import closing
from typing import Any, Mapping, Optional, Tuple, Callable, List, Dict

import yamlcfg

from .sources import Sources
from .sinks import Sinks

log = logging.getLogger(__name__)

class Router:
	def __init__(self, config: Mapping[str, Any]):
		self._config = config

		self._loop = None            # type: Optional[asyncio.BaseEventLoop]
		self.__control_lock = threading.Lock()

		# noinspection PyProtectedMember
		self._services_config = yamlcfg.YamlConfig(self._config['program']['services-config'])._data  # type: Dict[str, Any]

		self.sources = Sources(config)
		self.sinks = Sinks(config, self._services_config)

		# Establish communication channel between modules
		src_hooks = {
			'services_needed': self.sinks.services_needed,  # obtain service list for given source
			'change_detected': self.sinks.change_detected,  # notify sink about a change
			'service2sources': self.service2sources,        # convert canonical service name to (source, services) tuple
			'source2service': self.source2service           # convert source, service pair into canonical service name
		}
		sink_hooks = {
			'service_nodes': self.sources.service_nodes,    # obtain list of healthy nodes for canonical service
			'run_main_thread': self.run_main_thread,        # schedule task execution in the main thread
			'service2sources': self.service2sources         # convert canonical service name to (source, services) tuple
		}
		self.sources.set_hooks(src_hooks)
		self.sinks.set_hooks(sink_hooks)

		self._service2source = {}  # type: Dict[str, Tuple[str, str]]
		self._source2service = {}  # type: Dict[Tuple[str, str], str]
		self._setup()

	def _setup(self) -> None:
		# Generating canonical service -> (source, service) tuple
		for service_name, value in self._services_config.items():
			method, service = value['discovery']['method'], value['discovery']['service']
			self._service2source[service_name] = (method, service)
			self._source2service[(method, service)] = service_name

	def run(self) -> None:
		self.sinks.start()
		self.sources.start()

		with closing(asyncio.new_event_loop()) as loop:
			asyncio.set_event_loop(loop)

			with self.__control_lock:
				self._loop = loop

			# noinspection PyShadowingNames
			def signal_handler(signame):
				log.warning('Got %s, terminating ...', signame)
				loop.stop()

			for signame in ('SIGINT', 'SIGTERM'):
				loop.add_signal_handler(getattr(signal, signame), functools.partial(signal_handler, signame))

			loop.run_forever()

		self.sources.stop()
		self.sinks.stop()

	def run_main_thread(self, task: Callable[[], Any], *args: List[Any], **kwargs: Dict[str, Any]):
		"""
		Run function in the main thread and returns Future.
		:param task: function to call
		:param args: arguments to the function
		:param kwargs: keyword arguments to the function
		:return: future containing the result
		"""
		assert self._loop is not None

		async def coroutine():
			try:
				return task(*args, **kwargs)
			except Exception:
				log.exception("Got exception when executing a subroutine")
				raise

		with self.__control_lock:
			return asyncio.run_coroutine_threadsafe(coroutine(), self._loop)

	def service2sources(self, canonical_service: str, data_centers: Optional[str]) -> Tuple[str, List[str]]:
		"""
		Convert canonical service name to (source, service) tuple.
		:param canonical_service: name of the service
		:param data_center: data center where the service is located or None if the same
		:return: source, services tuple
		"""

		# TODO: this should be relocated once we get a better idea when we support more sources
		source, service = self._service2source[canonical_service]
		if data_centers:
			services = [ "%s/%s" % (dc, service) for dc in data_centers.split(' ') ]
		else:
			services = [ service ]

		return source, services

	def source2service(self, source: str, service: str) -> str:
		dc_service = service.split('/')
		if len(dc_service) > 1:
			service = dc_service[1]

		return self._source2service[(source, service)]
