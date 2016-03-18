import logging
from collections import defaultdict
from io import StringIO
from typing import Any, Dict, List

from .abstract import AbsSink

log = logging.getLogger(__name__)

class HAProxy(AbsSink):
	def __init__(self, config: Dict[str, Any]):
		super().__init__(config)

		self._config = config['sinks']['haproxy']  # type: Dict[str]
		self._service_config = config['services']  # type: Dict[str, dict]

	def generate_config(self) -> str:
		cnf = StringIO()

		cnf.write("global\n")
		for entry in self._config['global']:
			cnf.write("  %s\n" % entry)

		cnf.write("\ndefaults\n")
		for entry in self._config['defaults']:
			cnf.write("  %s\n" % entry)

		cnf.write("\nfrontend stats\n")
		cnf.write("  bind *:81\n")
		cnf.write("  stats enable\n")
		cnf.write("  stats uri /\n")
		cnf.write("  stats show-legends\n")
		cnf.write("  stats show-node\n")
		cnf.write("  stats refresh 60s\n")

		for service in self._config['services']:
			service_config = self._service_config[service]['haproxy']

			cnf.write("\nlisten %s\n" % service)
			cnf.write("  bind *:%d\n" % int(service_config['port']))
			for option in service_config['options']:
				cnf.write("  %s\n" % option)
			cnf.write("\n")

			for node in self._hooks['service_nodes'](service):
				cnf.write("  server %s %s:%d %s\n" % (node['name'], node['address'], node['port'], service_config['server_options']))

		return cnf.getvalue()

	def services_needed(self):
		result = defaultdict(list)  # type: Dict[str, List[str]]

		for service in self._config['services']:
			discovery = self._service_config[service]['discovery']  # type: Dict[str, str]
			result[discovery['method']].append(discovery['service'])

		return result
