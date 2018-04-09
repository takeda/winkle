import unittest
from pathlib import Path
from unittest import mock

from winkle.haproxy import HAProxy
from winkle.types import Node

path = Path(__file__)

def service_nodes(service, datacenter):
	return {
		'service-1': [
			Node('1.1.1.1', '1234', 'node1', {}, []),
			Node('2.2.2.2', '1234', 'node2', {}, [])
		],
		'service-2': [
			Node('3.3.3.3', '4321', 'node3', {'rack': 'ab-c'}, []),
			Node('4.4.4.4', '4321', 'node4', {'rack': 'de-f'}, [])
		]
	}[service]

def service2sources(name, datacenter):
	return {
		'service-1': ('consul', ['consul-service-1']),
		'service-2': ('marathon', ['marathon-service-1'])
	}[name]

class HAProxyTest(unittest.TestCase):
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
						'status': 'service haproxy status',
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
						{'service-2': {'rack-aware': True, 'minimum': 20}}
					],
					'extra': ['line 1', 'line 2']
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
			'service2sources': service2sources
		}

		HAProxy._sorting_key = None
		self.haproxy = HAProxy(config, services)
		self.haproxy.set_hooks(hooks)
		self.haproxy.start()

	def test_calculate_weights(self):
		node1 = Node('1.1.1.1', '1111', 'node1', {'rack': 'aa-a'}, [])
		node2 = Node('2.2.2.2', '2222', 'node2', {'rack': 'ab-c'}, [])
		node3 = Node('3.3.3.3', '3333', 'node3', {'rack': 'bb-b'}, [])
		node4 = Node('4.4.4.4', '4444', 'node4', {'weight': '42'}, [])
		node5 = Node('4.4.4.4', '4444', 'node5', {'weight': '24'}, [])
		node6 = Node('6.6.6.6', '6666', 'node6', {'weight': '25%'}, [])
		node7 = Node('7.7.7.7', '7777', 'node7', {'weight': '50%'}, [])
		node8 = Node('8.8.8.8', '8888', 'node8', {'weight': '0.5%'}, [])
		node9 = Node('9.9.9.9', '9999', 'node9', {'weight': '5.5%'}, [])

		with self.subTest("empty node list"), mock.patch('winkle.haproxy.log') as log:
			result = self.haproxy._calculate_weights([], False)
			log.error.assert_called_with("There's not a single static weight; treating percentage weights as weights")
			self.assertEqual(result, [])

		with self.subTest("basic list with no weights no rack awareness"):
			nodes = [node1, node2, node3]
			result = self.haproxy._calculate_weights(nodes, False)
			self.assertEqual(result, [(node1, 10), (node2, 10), (node3, 10)])

		with self.subTest("basic list with no weights with rack awareness"):
			nodes = [node1, node2, node3]
			result = self.haproxy._calculate_weights(nodes, True)
			self.assertEqual(result, [(node1, 10), (node2, 20), (node3, 10)])

		with self.subTest("list with static weights"):
			nodes = [node2, node4, node5]
			result = self.haproxy._calculate_weights(nodes, True)
			self.assertEqual(result, [(node2, 20), (node4, 42), (node5, 24)])

		with self.subTest("list with percentage weights"):
			nodes = [node4, node6, node7]
			result = self.haproxy._calculate_weights(nodes, True)
			self.assertEqual(result, [(node4, 42), (node6, 42), (node7, 84)])

		with self.subTest("list with only percentage weights"), mock.patch('winkle.haproxy.log') as log:
			nodes = [node6, node7]
			result = self.haproxy._calculate_weights(nodes, True)
			log.error.assert_called_with("There's not a single static weight; treating percentage weights as weights")
			self.assertEqual(result, [(node6, 25), (node7, 50)])

		with self.subTest("percentage weights adds to more than 100%"), mock.patch('winkle.haproxy.log') as log:
			nodes = [node1, node7, node7, node7]
			result = self.haproxy._calculate_weights(nodes, True)
			log.error.assert_called_with("Sum of percentage weights is equal or higher than 100% (%f); treating "
			                             "percentage weights as weights", 150.0)
			self.assertEqual(result, [(node1, 10), (node7, 50), (node7, 50), (node7, 50)])

		with self.subTest("fractional percentage (0.5%)"), mock.patch('winkle.haproxy.log') as log:
			nodes = [node1, node4, node8]
			result = self.haproxy._calculate_weights(nodes, False)
			log.warning.assert_called_with("%s's weight is calculated to %d; this node won't be receiving any traffic",
				node8.name, 0)
			self.assertEqual(result, [(node1, 10), (node4, 42), (node8, 0)])

		with self.subTest("fractional percentage (5.5%)"):
			nodes = [node1, node4, node9]
			result = self.haproxy._calculate_weights(nodes, False)
			self.assertEqual(result, [(node1, 10), (node4, 42), (node9, 3)])

	def test_config_generation(self):
		with path.with_name('haproxy.cfg').open() as f:
			expected = f.read()
		got = self.haproxy._generate_config()

		self.assertEqual(expected, got.decode())

	def test_services_needed(self):
		got = self.haproxy.services_needed
		self.assertDictEqual({'consul': ['consul-service-1'], 'marathon': ['marathon-service-1']}, got)
