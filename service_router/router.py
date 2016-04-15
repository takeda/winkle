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

		self._services_config = yamlcfg.YamlConfig(self._config['program']['services-config'])._data  # type: Dict[str, Any]

		self.sources = Sources(config)
		self.sinks = Sinks(config, self._services_config)

		# Establish communication channel between modules
		src_hooks = {
			'services_needed': self.sinks.services_needed,  # obtain service list for given source
			'change_detected': self.sinks.change_detected,  # notify sink about a change
			'service2source': self.service2source           # convert canonical service name to (source, service) tuple
		}
		sink_hooks = {
			'service_nodes': self.sources.service_nodes,    # obtain list of healthy nodes for canonical service
			'run_main_thread': self.run_main_thread,        # schedule task execution in main thread
			'service2source': self.service2source           # convert canonical service name to (source, service) tuple
		}
		self.sources.set_hooks(src_hooks)
		self.sinks.set_hooks(sink_hooks)

		self._service2source = {}  # type: Dict[str, Tuple[str, str]]
		self._setup()

	def _setup(self) -> None:
		# Generating canonical service -> (source, service) tuple
		for service_name, value in self._services_config.items():
			self._service2source[service_name] = (value['discovery']['method'], value['discovery']['service'])

	def run(self) -> None:
		self.sinks.start()
		self.sources.start()

		with closing(asyncio.new_event_loop()) as loop:
			asyncio.set_event_loop(loop)

			with self.__control_lock:
				self._loop = loop

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
		Run function in main thread and returns Future.
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

	def service2source(self, service: str) -> Tuple[str, str]:
		"""
		Convert canonical service name to (source, service) tuple.
		:param service: name of the service
		:return: source, service tuple
		"""
		return self._service2source[service]
