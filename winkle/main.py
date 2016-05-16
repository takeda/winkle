import logging.config
import sys
from copy import deepcopy
from typing import Any, Mapping

import click
import yamlcfg

from winkle import daemon, defaults
from winkle.router import Router
from winkle.utils import mergedict

class UserGroupParam(click.ParamType):
	name = 'user:group'

	def convert(self, value, param, ctx):
		values = value.split(':')
		user = values[0]
		group = values[1] if len(values) > 0 else None

		return user, group

USERGROUP = UserGroupParam()

@click.command()
@click.option('--install', is_flag=True, default=False, help='Install service')
@click.option('--foreground/--background', '-f', default=False, help='Run in foreground and log to console')
@click.option('--config', '-c', type=str, default='/etc/winkle/winkle.yaml', help='Configuration file')
@click.option('--pid-file', '-p', type=str, help='PID file')
@click.option('--log-file', '-l', type=str, help='Log file')
@click.option('--user', '-u', type=USERGROUP, help='User and group')
@click.version_option()
def main(install: bool, foreground: bool, config: str, pid_file: str, log_file: str, user: tuple):
	computed_config = deepcopy(defaults.default_config)
	yaml_config = yamlcfg.YamlConfig(paths=[config])._data
	mergedict(computed_config, yaml_config)

	if pid_file:
		computed_config['program']['pid-file'] = pid_file
	if log_file:
		computed_config['program']['log-gile'] = log_file
	if user:
		computed_config['program']['user'] = user[0]
		computed_config['program']['group'] = user[1]

	if install:
		daemon.install(computed_config)
		sys.exit()

	uidgid = daemon.get_ids(computed_config['program']['user'], computed_config['program']['group'])
	daemon.reduce_privileges(uidgid)

	defaults.log_config['handlers']['file']['filename'] = computed_config['program']['log-file']

	if foreground:
		defaults.log_config['root']['handlers'] = ['console']
		run(computed_config)
	else:
		daemon.daemonize(computed_config['program']['pid-file'], run, computed_config)

def run(yamlconfig: Mapping[str, Any]) -> None:
	logging.config.dictConfig(defaults.log_config)
	log = logging.getLogger(__name__)
	log.info("Winkle by Derek Kulinski <derek.kulinski@openx.com>")

	router = Router(yamlconfig)
	router.run()

if __name__ == '__main__':
	main()
