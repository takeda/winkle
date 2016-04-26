import asyncio
import functools
import logging
import time

import cachetools

log = logging.getLogger(__name__)

def async_index_cache(cache):
	def decorator(func):
		lock = asyncio.Lock()

		try:
			index_pos = func.__code__.co_varnames.index('index')
		except ValueError:
			index_pos = None

		async def wrapper(*args, **kwargs):
			k = cachetools.hashkey(*args, **kwargs)

			# Figure out index value from the arguments
			req_index = kwargs.get('index')
			if req_index is None and index_pos is not None and index_pos < len(args):
				req_index = args[index_pos]

			async with lock:
				index, value = cache.get(k, (0, None))

			if value is not None:
				if req_index is None or int(req_index) < index:
					log.debug("Cache hit (index %d)", index)
					return value

			log.debug("Cache miss; requesting data")
			v = await func(*args, **kwargs)
			index = int(v[0])

			try:
				async with lock:
					cache[k] = index, v
			except ValueError:
				pass  # value too large

			return v

		functools.update_wrapper(wrapper, func)
		return wrapper

	return decorator

def async_ttl_cache(ttl = 600, maxsize = 128, timer = time.time, getsizeof = None):
	return async_index_cache(cachetools.TTLCache(maxsize, ttl, timer, getsizeof))
