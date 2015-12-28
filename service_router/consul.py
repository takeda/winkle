import asyncio
import logging

import consul.aio
from .caching import async_ttl_cache

log = logging.getLogger(__name__)

class Consul:
	def __init__(self, loop, callbacks):
		self.callbacks = callbacks

		self.services = ['suanpan-riak', 'openx-app.broker']

		self.client = consul.aio.Consul('devint-consul-xv-01.xv.dc.openx.org', consistency = 'stale', loop = loop)

	async def monitor(self):
		index = None
		while True:
			i, response = await self._catalog_services()
			print(i)
			i, response = await self._catalog_service('suanpan-riak', index)
			print(i)
			if i == index:
				log.debug("Timeout")
				continue
			self.callbacks['update'](response)
			index = i

	@async_ttl_cache(60, 2)
	async def _catalog_services(self, index = None):
		return await self.client.catalog.services(index)

	@async_ttl_cache(60)
	async def _catalog_service(self, node, index = None):
		return await self.client.catalog.service(node, index)
