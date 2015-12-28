import asyncio
import functools
import logging
import time

import cachetools

log = logging.getLogger(__name__)

def async_cache(cache):
	def decorator(func):
		log.debug("Hello!")
		lock = asyncio.Lock()

		try: indexpos = func.__code__.co_varnames.index('index')
		except ValueError: indexpos = None

		async def wrapper(*args, **kwargs):
			k = cachetools.hashkey(*args, **kwargs)

			from_cache = False if 'index' in kwargs or (indexpos and indexpos < len(args) and args[indexpos]) else True

			if not ('index' in kwargs or (indexpos and indexpos < len(args) and args[indexpos])):
				log.debug("Trying to use cache")
				try:
					async with lock:
						return cache[k]
				except KeyError:
					pass # not in cache

			log.debug("Fetching data")
			v = await func(*args, **kwargs)

			try:
				async with lock:
					cache[k] = v
			except ValueError:
				pass # value too large

			return v

		functools.update_wrapper(wrapper, func)
		return wrapper

	return decorator

def async_ttl_cache(ttl = 600, maxsize = 128, timer = time.time, getsizeof = None):
	return async_cache(cachetools.TTLCache(maxsize, ttl, timer, getsizeof))
