from pathlib import Path
from unittest import TestCase

from service_router.haproxy import HAProxy

path = Path(__file__)

def service_nodes(service):
	return {
		'service-1': [
			{'name': 'node1', 'address': '1.1.1.1', 'port': 1234},
			{'name': 'node2', 'address': '2.2.2.2', 'port': 1234}
		],
		'service-2': [
			{'name': 'node3', 'address': '3.3.3.3', 'port': 4321},
			{'name': 'node4', 'address': '4.4.4.4', 'port': 4321}
		]
	}[service]

class HAProxyTest(TestCase):
	def setUp(self):
		config = {
			'sinks': {
				'haproxy': {
					'global': ['global setting 1', 'global setting 2'],
					'defaults': ['aa', 'bb', 'cc'],
					'services': ['service-1', 'service-2']
				}
			},
			'services': {
				'service-1': {
					'discovery': {
						'method': 'consul',
						'service': 'consul-service-1'
					},
					'haproxy': {
						'port': '1234',
						'options': ['option 1', 'option 2'],
						'server_options': 'check inter 10000 rise 3 fall 2'
					}
				},
				'service-2': {
					'discovery': {
						'method': 'marathon',
						'service': 'marathon-service-1'
					},
					'haproxy': {
						'port': '4321',
						'options': ['option 3', 'option 4'],
						'server_options': 'check inter 10s rise 3 fall 2'
					}
				}
			}
		}

		hooks = {
			'service_nodes': service_nodes
		}

		self.haproxy = HAProxy(config)
		self.haproxy.set_hooks(hooks)

	def test_config_generation(self):
		with path.with_name('haproxy.cfg').open() as f:
			expected = f.read()
		got = self.haproxy.generate_config()

		self.assertEqual(expected, got)

	def test_services_needed(self):
		got = self.haproxy.services_needed()
		self.assertDictEqual({'consul': ['consul-service-1'], 'marathon': ['marathon-service-1']}, got)
