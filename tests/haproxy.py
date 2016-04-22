from pathlib import Path
from unittest import TestCase

from winkle.haproxy import HAProxy
from winkle.types import Node

path = Path(__file__)

def service_nodes(service):
	return {
		'service-1': [
			Node('1.1.1.1', '1234', 'node1', None, None),
			Node('2.2.2.2', '1234', 'node2', None, None)
		],
		'service-2': [
			Node('3.3.3.3', '4321', 'node3', {'rack': 'ab-c'}, None),
			Node('4.4.4.4', '4321', 'node4', {'rack': 'de-f'}, None)
		]
	}[service]

def service2source(name):
	return {
		'service-1': ('consul', 'consul-service-1'),
		'service-2': ('marathon', 'marathon-service-1')
	}[name]

class HAProxyTest(TestCase):
	def setUp(self):
		self.maxDiff = None

		config = {
			'program': {
				'rack': 'ab-c'
			},
			'sinks': {
				'haproxy': {
					'service': {
						'config': 'haproxy.cfg',
						'check-config': 'haproxy -c -f {file}',
						'start': 'service haproxy start',
						'reload': 'service haproxy reload',
						'pid-file': '/var/run/haproxy.pid',
						'state-file': '/var/lib/haproxy.state',
						'socket': '/var/lib/haproxy.sock'
					},
					'global': ['global setting 1', 'global setting 2'],
					'defaults': ['aa', 'bb', 'cc'],
					'services': [
						'service-1',
						{'service-2': {'rack-aware': True}}
					]
				}
			}
		}

		services = {
			'service-1': {
				'discovery': {
					'method': 'consul',
					'service': 'consul-service-1'
				},
				'haproxy': {
					'options': ['bind *:1234', 'option 1', 'option 2'],
					'server_options': 'check inter 10000 rise 3 fall 2'
				}
			},
			'service-2': {
				'discovery': {
					'method': 'marathon',
					'service': 'marathon-service-1'
				},
				'haproxy': {
					'options': ['bind *:4321', 'option 3', 'option 4'],
					'server_options': 'check inter 10s rise 3 fall 2'
				}
			}
		}

		hooks = {
			'service_nodes': service_nodes,
			'service2source': service2source
		}

		self.haproxy = HAProxy(config, services)
		self.haproxy._sorting_key = None
		self.haproxy.set_hooks(hooks)
		self.haproxy.start()

	def test_config_generation(self):
		with path.with_name('haproxy.cfg').open() as f:
			expected = f.read()
		got = self.haproxy._generate_config()

		self.assertEqual(expected, got.decode())

	def test_services_needed(self):
		got = self.haproxy.services_needed
		self.assertDictEqual({'consul': ['consul-service-1'], 'marathon': ['marathon-service-1']}, got)
