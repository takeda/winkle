import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Any, Mapping

log = logging.getLogger(__name__)

class UpdateError(Exception):
	pass

class ServiceUpdater:
	def __init__(self, config: Mapping[str, Any]):
		self._config_file = Path(config['config'])

		name = self._config_file.name
		self._config_file_new = self._config_file.with_name('.%s' % name)
		self._config_file_backup = self._config_file.with_name('%s~bak' % name)

		self._pidfile = config['pid-file']       # type: str
		self._checkcfg = config['check-config']  # type: str
		self._status = config['status']          # type: str
		self._start = config['start']            # type: str
		self._reload = config['reload']          # type: str

	def needs_update(self, new_config: bytes) -> bool:
		new_hash = self._compute_hash(new_config)
		old_hash = self._get_file_hash()

		return new_hash != old_hash

	def update_config(self, new_config: bytes) -> None:
		"""Update configuration
		:param new_config new configuration
		:raises UpdateError
		"""
		log.info("Writing new configuration to %s", self._config_file_new)
		with self._config_file_new.open('wb') as of:
			of.write(new_config)

		log.info("Validating %s", self._config_file_new)
		if not self.validate_config(str(self._config_file_new)):
			raise UpdateError("Generated config is not valid.")

		if self._config_file.is_file():
			log.debug("Creating backup file: %s", self._config_file_backup)
			self._config_file.rename(self._config_file_backup)

		log.info("Installing new config in %s" % self._config_file)
		self._config_file_new.rename(self._config_file)

	def validate_config(self, file: str) -> bool:
		log.debug("Validating config %s", file)
		return subprocess.call(self._checkcfg.format(config=file), shell=True) == 0

	def is_running(self) -> bool:
		return subprocess.call(self._status.format(pidfile=self._pidfile), shell=True) == 0

	def start(self) -> bool:
		return subprocess.call(self._start.format(config=self._config_file, pidfile=self._pidfile), shell=True) == 0

	def reload(self) -> bool:
		return subprocess.call(self._reload.format(config=self._config_file, pidfile=self._pidfile), shell=True) == 0

	def _get_file_hash(self) -> str:
		"""
		Computes hash of the configuration file
		:return: computed hash or empty string when file does not exist
		"""

		if not self._config_file.is_file():
			return ''

		with self._config_file.open('rb') as f:
			return self._compute_hash(f.read())

	@staticmethod
	def _compute_hash(data: bytes) -> str:
		return hashlib.md5(data).hexdigest()