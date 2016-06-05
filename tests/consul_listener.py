from unittest import TestCase

from winkle import consul_listener

class ConsulListener(TestCase):
	def test_get_monitor_services(self):
		monitors = consul_listener.ConsulListener._get_monitor_services(['service1', 'service2', 'dc1/service3',
		                                                                 'dc2/service4', 'dc1/service5'])
		self.assertEqual(monitors, ['service1', 'dc1/service3', 'dc2/service4'])
