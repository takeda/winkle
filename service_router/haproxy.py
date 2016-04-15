import logging
from collections import defaultdict, OrderedDict
from io import StringIO
from typing import Any, Dict, Mapping

from .abstract import AbsSink, T_SERVICES
from .errors import ConfigError
from .haproxy_comm import HAProxyComm
from .node import node_random_sort_key
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

	def process_update(self, source, added, removed, updated):
		assert self._initialized

		log.debug("Generating config")
		new_config = self._generate_config()
		log.debug("Finished generating config")
		if not self._service_updater.needs_update(new_config):
			log.info("No change in config, skipping")
			return

		log.info("Writing config")
		self._service_updater.update_config(new_config)
		log.info("Writing state file")
		self._comm.save_state(self._state_file)
		log.info("Finished writing config")
		self._service_updater.reload_config()
