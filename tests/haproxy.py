from pathlib import Path
from unittest import TestCase

from service_router.haproxy import HAProxy
from service_router.node import Node

path = Path(__file__)

def service_nodes(service):
	return {
		'service-1': [
			Node('1.1.1.1', '1234', 'node1', None, None),
			Node('2.2.2.2', '1234', 'node2', None, None)
		],
		'service-2': [
			Node('3.3.3.3', '4321', 'node3', None, None),
			Node('4.4.4.4', '4321', 'node4', None, None)
		]
	}[service]

class HAProxyTest(TestCase):
	def setUp(self):
		self.maxDiff = None

		config = {
			'sinks': {
				'haproxy': {
					'service': {
						'config': 'haproxy.cfg',
						'checkcfg': 'haproxy -c -f {file}',
						'start': 'service haproxy start',
						'reload': 'service haproxy reload'
					},
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
		got = self.haproxy._generate_config()

		self.assertEqual(expected, got)

	def test_services_needed(self):
		got = self.haproxy.services_needed
		self.assertDictEqual({'consul': ['consul-service-1'], 'marathon': ['marathon-service-1']}, got)
