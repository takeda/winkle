#! /usr/bin/env python3

import asyncio
from asyncio import ensure_future
from functools import partial
import logging

from consul.aio import Consul

from service_router.caching import async_ttl_cache

log = logging.getLogger(__name__)

class ConsulListener:
	def __init__(self, loop):
		self.loop = loop
		self.consul = Consul("devint-consul-xv-01.xv.dc.openx.org", consistency = 'stale', loop = loop)
		self.services = ['riak-suanpan', 'openx-app.broker']

	def run(self, services):
		self.tasks = {
			service: ensure_future(self._monitor(service), loop = self.loop)
				for service in services
		}

		self.loop.run_until_complete(asyncio.wait(self.tasks.values()))

	async def _monitor(self, service):
		log.debug("Starting monitoring of %s" % (service,))

		index = None
		while True:
			i, response = await self._health_service(service, index)
			print("%s: got index %s" % (service, i))

			if i == index:
				log.debug("%s - timeout" % (service,))
				continue

			self.callback(response)
			index = i

	@async_ttl_cache(60)
	async def _health_service(self, service, index = None):
		print("Checking service", service)
		index, response = await self.consul.health.service(service, index, '5s', passing = True)
		print(service, "got response", index)

		services = []
		for node in response:
			attrs, tags = [], []
			for tag in node['Service']['Tags']:
				if '=' in tag:
					attrs.append(tuple(tag.split('=')))
				else:
					tags.append(tag)

			services.append({
				'address': node['Service']['Address'],
				'port': node['Service']['Port'],
				'attrs': attrs,
				'tags': tags
			})

		return index, services

	def callback(self, response):
		print("Callback: %r" % response)

if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG)
	loop = asyncio.get_event_loop()
	loop.set_debug(False)
	listener = ConsulListener(loop)
	listener.run(listener.services)
	loop.close()
