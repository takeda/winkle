import logging
from collections import defaultdict, OrderedDict
from io import StringIO
from typing import Any, Dict, Mapping

from .abstract import AbsSink, T_SERVICES
from .errors import ConfigError
from .haproxy_comm import HAProxyComm
from .types import node_random_sort_key, T_CHANGES
from .service_updater import ServiceUpdater

T_SERVICES_CONFIG = Dict[str, Dict[str, Any]]

log = logging.getLogger(__name__)

STATS_CONFIG = [
	'bind *:1024',
	'mode http',
	'stats enable',
	'stats uri /',
	'stats show-legends',
	'stats show-node',
	'stats refresh 60s',
	'monitor-uri /alive'
]


class HAProxy(AbsSink):
	def __init__(self, config: Mapping[str, Any], services: Mapping[str, Any]):
		super().__init__(config)

		self._config = config['sinks']['haproxy']  # type: Dict[str]
		self._rack = config['program'].get('rack')
		self._service_config = services
		self._state_file = self._config['service']['state-file']  # type: str

		self._service_updater = ServiceUpdater(self._config['service'])
		self._comm = HAProxyComm(self._config['service']['socket'])

		self._services = OrderedDict()                # type: T_SERVICES_CONFIG
		self._monitored_services = defaultdict(list)  # type: T_SERVICES
		self._setup()

	def _setup(self) -> None:
		# Generate list of canonical services with configuration
		for service_name in self._config['services']:
			defaults = {
				'rack_aware': False,
				'minimum': 0
			}

			if isinstance(service_name, dict):
				if len(service_name) != 1:
					raise ConfigError('Dictionary needs to have only one element (perhaps you forgot'
					                  'a minus sign in yaml config?)')

				name = list(service_name)[0]
				self._services[name] = defaults
				self._services[name].update(service_name[name])
			else:
				self._services[service_name] = defaults

	def start(self) -> None:
		for service_name in self._services:
			source, service = self._hooks['service2source'](service_name)
			self._monitored_services[source].append(service)

		self._initialized = True

	def _generate_config(self) -> bytes:
		assert self._initialized

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
			for node in sorted(self._hooks['service_nodes'](service), key=node_random_sort_key):
				same_rack = self._same_rack(node.attrs.get('rack')) if config['rack_aware'] else True

				nodes.append('server %s %s:%s %s%s' % (node.name, node.address, node.port,
				                                       service_config['server_options'],
				                                       ' weight 10' if same_rack else ' weight 100'))

			cnf.writelines(format(nodes))

		return cnf.getvalue().encode()

	def _same_rack(self, rack: str) -> bool:
		if rack is None or self._rack is None:
			return True

		return self._rack == rack

	@property
	def services_needed(self):
		assert self._initialized

		return self._monitored_services

	def process_update(self, source: str, changes: T_CHANGES) -> None:
		assert self._initialized

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
					log.warning("%s/%s is being removed but haproxy doesn't recognize it", backend, server.name)
					continue

				if self._comm.is_server_disabled(backend, server.name, state):
					log.warning("%s/%s is being removed but haproxy doesn't recognize it", backend, server.name)
					continue

				disable[backend].append(server.name)

		log.debug("Generating config")
		new_config = self._generate_config()
		if not self._service_updater.needs_update(new_config):
			log.info("No change in config, skipping")
			return

		self._service_updater.update_config(new_config)

		if not reload:
			for backend, servers in disable.items():
				for server in servers:
					log.info('disabling %s/%s', backend, server)
					self._comm.disable_server(backend, server)
		else:
			log.info("Writing state file to %s", self._state_file)
			self._comm.save_state(self._state_file)
			self._service_updater.reload_config()
