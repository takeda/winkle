import logging
from collections import defaultdict
from io import StringIO
from typing import Any, Dict, List, Mapping

from .abstract import AbsSink, T_SERVICES
from .errors import ConfigError
from .haproxy_comm import HAProxyComm
from .node import node_random_sort_key
from .service_updater import ServiceUpdater

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
		self._service_config = services
		self._state_file = self._config['service']['state-file']  # type: str

		self._service_updater = ServiceUpdater(self._config['service'])
		self._comm = HAProxyComm(self._config['service']['socket'])
		self._monitored_services = self._setup()
		# TODO: use service-router style services in haproxy; let specific modules decode

	def _setup(self) -> T_SERVICES:
		result = defaultdict(list)  # type: T_SERVICES

		for service in self._config['services']:
			if isinstance(service, dict):
				if len(service) == 1:
					service = list(service)[0]
				else:
					raise ConfigError('Dictionary needs to have only one element (perhaps you forgot'
					                  'a minus sign in yaml config?)')

			discovery = self._service_config[service]['discovery']  # type: Dict[str, str]
			result[discovery['method']].append(discovery['service'])

		return result

	def _generate_config(self) -> bytes:
		def format(lines, level=1):
			return map(lambda x: '%s%s\n' % ('\t' * level, x), lines)

		cnf = StringIO()

		cnf.write("global\n")
		cnf.writelines(format(self._config['global']))

		cnf.write("\ndefaults\n")
		cnf.writelines(format(self._config['defaults']))

		cnf.write("\nfrontend stats\n")
		cnf.writelines(format(STATS_CONFIG))

		for service in self._config['services']:
			if isinstance(service, dict):
				if len(service) == 1:
					service = list(service)[0]
				else:
					raise ConfigError('Dictionary needs to have only one element (perhaps you forgot'
					                  'a minus sign in yaml config?)')

			service_config = self._service_config[service]['haproxy']

			cnf.write("\nlisten %s\n" % service)
			cnf.writelines(format(service_config['options']))
			cnf.write("\n")

			cnf.writelines(format([
				'server %s %s:%s %s' % (node.name, node.address, node.port, service_config['server_options'])
			        for node in sorted(self._hooks['service_nodes'](service), key=node_random_sort_key)
			]))

		return cnf.getvalue().encode()

	@property
	def services_needed(self):
		return self._monitored_services

	def process_update(self, source, added, removed, updated):
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
