__all__ = ['Error', 'UnhandledException', 'ConstraintFailedError', 'ConnectionError', 'HTTPResponseError', 'ConfigError']

class Error(Exception):
	pass

class UnhandledException(Error):
	pass

class ConstraintFailedError(Error):
	pass

# noinspection PyShadowingBuiltins
class ConnectionError(Error):
	pass

class HTTPResponseError(Error):
	def __init__(self, status, reason, message):
		self._status = status
		self._reason = reason
		self._message = message

	def __str__(self):
		return '%s %s, message=%r' % (self._status, self._reason, self._message)

class ConfigError(Error):
	pass
