from unittest import TestCase

from winkle import consul

class Consul(TestCase):
	def test_datacenter(self):
		with self.subTest('Plain service name'):
			dc, service = consul.Consul.data_center('test service')
			self.assertIsNone(dc)
			self.assertEqual(service, 'test service')

		with self.subTest('Service name with a slash prefix'):
			dc, service = consul.Consul.data_center('/test service')
			self.assertIsNone(dc)
			self.assertEqual(service, 'test service')

		with self.subTest('Service name with data center'):
			dc, service = consul.Consul.data_center('data center/test service')
			self.assertEqual(dc, 'data center')
			self.assertEqual(service, 'test service')
