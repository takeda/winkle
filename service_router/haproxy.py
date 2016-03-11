from io import StringIO

class HAProxy:
	def __init__(self, config):
		self.hooks = None

		self._config = config['sinks']['haproxy']
		self._service_config = config['services']

	def set_hooks(self, hooks):
		self.hooks = hooks

	def generate_config(self):
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

			for node in self.hooks['service_nodes'](service):
				cnf.write("  server %s %s:%d %s\n" % (node['name'], node['address'], node['port'], service_config['server_options']))

		return cnf.getvalue()
