import asyncio
import functools
import logging
import time

import cachetools

log = logging.getLogger(__name__)

def async_cache(cache):
	def decorator(func):
		lock = asyncio.Lock()

		try:
			index_pos = func.__code__.co_varnames.index('index')
		except ValueError:
			index_pos = None

		async def wrapper(*args, **kwargs):
			k = cachetools.hashkey(*args, **kwargs)

			if not ('index' in kwargs or (index_pos and index_pos < len(args) and args[index_pos])):
				try:
					async with lock:
						return cache[k]
				except KeyError:
					log.debug("Cache miss; requesting data")

			v = await func(*args, **kwargs)

			try:
				async with lock:
					cache[k] = v
			except ValueError:
				pass  # value too large

			return v

		functools.update_wrapper(wrapper, func)
		return wrapper

	return decorator

def async_ttl_cache(ttl = 600, maxsize = 128, timer = time.time, getsizeof = None):
	return async_cache(cachetools.TTLCache(maxsize, ttl, timer, getsizeof))
