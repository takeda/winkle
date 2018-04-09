import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

from winkle.router import Router

path = Path(__file__)

class RouterTest(unittest.TestCase):

	def testService2Sources(self):
		service_list = {
			'service-1': {
				'discovery': {
					'method': 'consul',
					'service': 'consul-service-1'
				},
				'haproxy': {
					'options': ['bind *:1234', 'option 1', 'option 2'],
					'server_options': 'check inter 10000 rise 3 fall 2'
				}
			}
		}

		config = {
			'program': {
				'rack': 'ab-c',
                                'services-config': service_list
			},
			'sources': {
				'consul': {}
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
						{'service-1': {'data-center': 'dc1 dc2', 'minimum': 20}}
					]
				}
			}
		}

		class yamlresult:
			def __init__(self, service_list):
				self._data = service_list

		with patch('yamlcfg.YamlConfig', return_value = yamlresult(service_list)) as yamlloader:
			router = Router(config)

		source, services = router.service2sources('service-1', 'dc1 dc2')
		self.assertEqual(source, 'consul')
		self.assertEqual(len(services), 2)
		self.assertEqual(services[0], 'dc1/consul-service-1')
		self.assertEqual(services[1], 'dc2/consul-service-1')

		source, services = router.service2sources('service-1', None)
		self.assertEqual(source, 'consul')
		self.assertEqual(len(services), 1)
		self.assertEqual(services[0], 'consul-service-1')
