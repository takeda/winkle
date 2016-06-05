import logging
import urllib.parse
from enum import Enum
from typing import Any, Mapping, Optional, Tuple

import aiohttp

from .errors import ConnectionError, UnhandledException, HTTPResponseError, Error

log = logging.getLogger(__name__)

class Consistency(Enum):
	Default = 1
	Consistent = 2
	Stale = 3

class Consul:
	def __init__(self, host: str='127.0.0.1', port: str='8500', scheme: str='http',
			consistency: Consistency=Consistency.Default, limit: Optional[int]=10):

		self._host = host
		self._port = port
		self._scheme = scheme
		self._consistency = consistency
		self._limit = limit

		self._base_url = '%s://%s:%s' % (self._scheme, self._host, self._port)

		connector = aiohttp.TCPConnector(limit=limit)
		self._session = aiohttp.ClientSession(connector=connector)

		self.health = Health(self)

	def consistency(self, params: dict, consistency: Optional[Consistency]=None) -> None:
		if not consistency:
			consistency = self._consistency

		if consistency == Consistency.Consistent:
			params.update({'Consistent': True})
		elif consistency == Consistency.Stale:
			params.update({'Stale': True})

	@staticmethod
	def blocking(params: dict, index: Optional[str], wait: Optional[str]) -> None:
		if index:
			params.update({'index': index})
			if wait:
				params.update({'wait': wait})

	@staticmethod
	def data_center(name: str) -> Tuple[Optional[str], str]:
		"""
		Processes a service name, if the name contains slash splits it into datacenter and service
		:param name: name of the service as listed in the configuration file
		:return: tuple conatining datacenter and service name, if there's no datacenter then first element is None
		"""
		dc_service = name.split('/')

		if len(dc_service) == 1:
			return None, name

		if not dc_service[0]:
			dc_service[0] = None

		return dc_service[0], dc_service[1]

	async def get(self, path: str, params: Optional[dict]=None) -> Tuple[aiohttp.HttpMessage, Mapping[str, Any]]:
		"""
		Makes a get request to consul and returns headers and json response
		:param path: path for the request
		:param params: dictionary of parameters
		:return: tuple containing a headers object and json converted to python dictionary/list
		:raises ConnectionError when connection was unable to connect to Consul
		:raises HTTPResponseError when received an unexpected response from Consul
		:raises UnhandledException for any exception that was not anticipated
		"""

		url = urllib.parse.urljoin(self._base_url, path)

		try:
			async with self._session.get(url, params=params) as resp:  # type: aiohttp.client_reqrep.ClientResponse
				if resp.status != 200:
					raise HTTPResponseError(resp.status, resp.reason, await resp.text())

				if resp.headers['content-type'] != 'application/json':
					raise HTTPResponseError(resp.status, resp.reason, await resp.text())

				return resp.headers, await resp.json()

		except (aiohttp.errors.ClientResponseError, aiohttp.errors.ClientOSError) as e:
			raise ConnectionError(e) from e
		except Error:
			raise
		except Exception as e:
			raise UnhandledException('Got an unexpected exception') from e

	def close(self) -> None:
		"""
		Closes the current session
		"""
		self._session.close()

class Health:
	def __init__(self, agent: Consul):
		self._agent = agent

	async def service(self, service: str, index: str = None, wait: str = None,
			passing: bool = None, consistency: Consistency = None) -> Tuple[str, Mapping[str, Any]]:

		params = {}
		dc, service = self._agent.data_center(service)
		if dc:
			params['dc'] = dc

		self._agent.consistency(params, consistency)
		self._agent.blocking(params, index, wait)
		if passing:
			params['passing'] = True

		path = urllib.parse.urljoin('/v1/health/service/', urllib.parse.quote(service))

		headers, data = await self._agent.get(path, params)

		return headers['x-consul-index'], data
