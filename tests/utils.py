from copy import deepcopy
from unittest import TestCase

from winkle import utils

class Utils(TestCase):
	def setUp(self):
		self.maxDiff = None
		self.default = {
			'program': {
				'services-config': '/etc/winkle/services.yaml',
				'rack': None,
				'user': 'nobody',
				'group': 'nobody',
				'log-file': '/var/log/winkle/winkle.log',
				'pid-file': '/var/run/winkle/winkle.pid'
			},
			'sources': {
				'consul': {
					'host': '127.0.0.1',
					'port': 8500,
					'consistency': 'stale'
				}
			},
			'sinks': {
				'haproxy': {
					'service': {
						'config': '/etc/haproxy/haproxy.cfg',
						'status': 'sudo service haproxy status',
						'start': 'sudo service haproxy start',
						'reload': 'sudo service haproxy reload',
						'pid-file': '/var/run/haproxy.pid',
						'check-config': '/usr/sbin/haproxy -c -f {config}'
					},
					'global': [
						'stats socket /tmp/haproxy.sock mode 660 level admin',
						'server-state-file /var/run/winkle/haproxy.state'
					],
					'defaults': [
						'retries 3',
						'timeout connect 5s',
						'timeout client 10m',
						'timeout server 10m',
						'load-server-state-from-file global'
					],
					'services': []
				}
			}
		}
		self.config = {
			'program': {
				'rack': 'lb-dl'
			},
			'sinks': {
				'haproxy': {
					'services': [
						'riak-suanpan-pb'
					]
				}
			}
		}
		self.merged = {
			'program': {
				'services-config': '/etc/winkle/services.yaml',
				'rack': 'lb-dl',
				'user': 'nobody',
				'group': 'nobody',
				'log-file': '/var/log/winkle/winkle.log',
				'pid-file': '/var/run/winkle/winkle.pid'
			},
			'sources': {
				'consul': {
					'host': '127.0.0.1',
					'port': 8500,
					'consistency': 'stale'
				}
			},
			'sinks': {
				'haproxy': {
					'service': {
						'config': '/etc/haproxy/haproxy.cfg',
						'status': 'sudo service haproxy status',
						'start': 'sudo service haproxy start',
						'reload': 'sudo service haproxy reload',
						'pid-file': '/var/run/haproxy.pid',
						'check-config': '/usr/sbin/haproxy -c -f {config}'
					},
					'global': [
						'stats socket /tmp/haproxy.sock mode 660 level admin',
						'server-state-file /var/run/winkle/haproxy.state'
					],
					'defaults': [
						'retries 3',
						'timeout connect 5s',
						'timeout client 10m',
						'timeout server 10m',
						'load-server-state-from-file global'
					],
					'services': [
						'riak-suanpan-pb'
					]
				}
			}
		}

	def test_dictmerge(self):
		computed = deepcopy(self.default)
		utils.mergedict(computed, self.config)
		self.assertDictEqual(computed, self.merged)
