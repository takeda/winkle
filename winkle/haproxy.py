import logging
from collections import defaultdict, OrderedDict
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Mapping

from .abstract import AbsSink, T_SERVICES
from .errors import ConfigError
from .haproxy_comm import HAProxyComm
from .types import node_random_sort_key, T_CHANGES
from .service_updater import ServiceUpdater

T_SERVICES_CONFIG = Dict[str, Dict[str, Any]]

log = logging.getLogger(__name__)

STATS_CONFIG = [
	'bind :1024',
	'mode http',
	'stats enable',
	'stats uri /',
	'stats show-legends',
	'stats show-node',
	'stats refresh 60s',
	'monitor-uri /alive'
]


class HAProxy(AbsSink):
	_sorting_key = node_random_sort_key

	def __init__(self, config: Mapping[str, Any], services: Mapping[str, Any]):
		super().__init__(config)

		self._config = config['sinks']['haproxy']  # type: Dict[str]
		self._rack = config['program'].get('rack')
		self._service_config = services
		self._state_file = Path(self._config['service']['state-file'])

		self._service_updater = ServiceUpdater(self._config['service'])
		self._comm = HAProxyComm(self._config['service']['socket'])

		# dictionary in form of canonical service name -> dict containing options
		self._services = OrderedDict()                # type: T_SERVICES_CONFIG

		# dictionary in form of source -> internal list of services (for cached lookups)
		self._monitored_services = defaultdict(list)  # type: T_SERVICES

		self._setup()

	def _setup(self) -> None:
		# Generate list of canonical services with configuration
		for service_name in self._config['services']:
			defaults = {
				'rack-aware': False,
				'minimum': 0,
				'data-center': None
			}

			if isinstance(service_name, dict):
				if len(service_name) != 1:
					raise ConfigError('Dictionary needs to have only one element (perhaps you forgot'
					                  'a dash in yaml config?)')

				name = list(service_name)[0]
				self._services[name] = defaults
				self._services[name].update(service_name[name])
			else:
				self._services[service_name] = defaults

	def start(self) -> None:
		for service_name, options in self._services.items():
			source, service = self._hooks['service2source'](service_name, options.get('data-center'))
			self._monitored_services[source].append(service)

		self._initialized = True

	def _generate_config(self) -> bytes:
		assert self._initialized

		# noinspection PyShadowingBuiltins
		def format(lines, level=1):
			return map(lambda x: '%s%s\n' % ('\t' * level, x), lines)

		cnf = StringIO()

		cnf.write("global\n")
		cnf.writelines(format(self._config['global']))

		cnf.write("\ndefaults\n")
		cnf.writelines(format(self._config['defaults']))

		cnf.write("\nfrontend stats\n")
		cnf.writelines(format(STATS_CONFIG))

		for service, config in self._services.items():
			service_config = self._service_config[service]['haproxy']

			cnf.write("\nlisten %s\n" % service)
			cnf.writelines(format(service_config['options']))
			cnf.write("\n")

			nodes = []

			sorted_nodes = sorted(self._hooks['service_nodes'](service, config.get('data-center')),
					key=self.__class__._sorting_key)

			weights = self.calculate_weights(sorted_nodes, config)

			for node, weight in zip(sorted_nodes, weights):
				nodes.append('server %s %s:%s %s%s' % (node.name, node.address, node.port,
				                                       service_config['server_options'],
				                                       ' weight %s' % weight))

			cnf.writelines(format(nodes))

		if len(self._config['extra']) > 0:
			cnf.write("\n# Extra configuration added (you should normally avoid this setting)\n")
			cnf.writelines(format(self._config['extra'], level=0))

		return cnf.getvalue().encode()

	def calculate_weights(self, nodes, config) -> list:
		assert self._initialized
		if not nodes:
			return []

		pcts = [None for n in nodes]
		pct_rem = 1.0

		rem_node_count = 0

		for n in range(len(nodes)):
			node = nodes[n]
			canary_pct = node.attrs.get('canaryPct')
			if canary_pct is not None:
				canary_pct = float(canary_pct)
				pcts[n] = canary_pct
				pct_rem = pct_rem - canary_pct
			else:
				rem_node_count = rem_node_count + 1

		if rem_node_count > 0:
			rem_pct_per = pct_rem / rem_node_count
			for p in range(len(pcts)):
				if pcts[p] is not None:
					continue
				else:
					same_rack = self._same_rack(node.attrs.get('rack')) if config['rack-aware'] else True
					pcts[p] = rem_pct_per if same_rack else rem_pct_per / 10.0

		min_pct = min(pcts)
		scale_factor = 1.0 if min_pct <= 0 else 1.0 / min_pct
		weights = [int(p * scale_factor) for p in pcts]
		return weights

	def _same_rack(self, rack: str) -> bool:
		if rack is None or self._rack is None:
			return True

		return self._rack == rack

	@property
	def services_needed(self):
		assert self._initialized

		return self._monitored_services

	def _incremental_update(self, changes: T_CHANGES) -> bool:
		"""
		Decide whether service needs to be reloaded or updated, and enable/disable services as needed

		logic:
		for each backend:
		  - if entries in updated set -> reload
		  - for added host
		    - if new backend -> reload
		    - if new host is added -> reload
		    - if host is disabled -> enable
		  - if config reload, skip to next backend
		  - for removed host
		    - if host not in state -> force reload (bug?)
		    - if host already disabled -> force reload (bug?)
		    - add to disabled list
		if no reload is necessary, disable nodes on the list

		:param changes: list of incremental changes
		:return: should service be reloaded
		"""

		backends = self._comm.get_backends()

		reload = False
		disable = defaultdict(list)
		for backend, change in changes.items():
			log.debug("Changes for %s: %r", backend, change)

			if len(change.updated) > 0:
				log.debug('We have updates for %s; forcing reload', backend)
				reload = True

			if backend not in backends:
				log.debug('%s is new; forcing reload', backend)
				reload = True
				continue

			state = self._comm.get_servers_state(backend)

			for server in change.added:
				if server.name not in state:
					log.debug('%s is new; forcing reload', server.name)
					reload = True
					continue

				if self._comm.is_server_disabled(backend, server.name, state):
					log.info('enabling %s/%s', backend, server.name)
					self._comm.enable_server(backend, server.name)

			# No need to disable if we are reloading anyway
			if reload:
				continue

			for server in change.removed:
				if server.name not in state:
					log.error("%s/%s is being removed but haproxy doesn't recognize it; forcing reload", backend,
						server.name)
					reload = True
					break

				if self._comm.is_server_disabled(backend, server.name, state):
					log.error("%s/%s is being removed but haproxy doesn't recognize it; forcing reload", backend,
						server.name)
					reload = True
					break

				disable[backend].append(server.name)

		if not reload:
			for backend, servers in disable.items():
				for server in servers:
					log.info('disabling %s/%s', backend, server)
					self._comm.disable_server(backend, server)

		return reload

	def process_update(self, source: str, changes: T_CHANGES) -> None:
		assert self._initialized

		running = self._service_updater.is_running()
		if self._comm.has_socket():
			reload = self._incremental_update(changes) if running else False
		else:
			reload = True

		log.debug("Generating config")
		new_config = self._generate_config()

		if self._service_updater.needs_update(new_config):
			log.info("Config is different; updating")
			self._service_updater.update_config(new_config)
		else:
			log.info("No change in config; skipping update")
			reload = False  # if we didn't modify the file there's no point reloading

		if not running:
			log.info("HAProxy is not running; starting the service")

			# State file existing at this point is invalid
			if self._state_file.exists():
				self._state_file.unlink()

			self._service_updater.start()
		elif reload:
			if self._comm.has_socket():
				log.info("Writing state file to %s", self._state_file)
				self._comm.save_state(self._state_file)

			log.info("Reloading haproxy")
			self._service_updater.reload()

			# Remove state file after reload
			if self._state_file.exists():
				self._state_file.unlink()
