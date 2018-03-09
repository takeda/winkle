import logging.config
import sys
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yamlcfg

from winkle import daemon, defaults
from winkle.router import Router
from winkle.utils import mergedict
from winkle.version import version

def user_group_param(value):
	values = value.split(':')

	user = values[0]
	group = values[1] if len(values) > 1 else None

	return user, group

def main():
	parser = ArgumentParser()
	parser.add_argument('--install', action='store_true', help='install service')
	group = parser.add_mutually_exclusive_group()
	group.add_argument('--foreground', '-f', action='store_true', help='run in foreground and log to console')
	group.add_argument('--background', action='store_true')
	parser.add_argument('--config', '-c', type=str, help='configuration file', metavar='FILE')
	parser.add_argument('--pid-file', '-p', type=str, help='PID file', metavar='FILE')
	parser.add_argument('--log-file', '-l', type=str, help='log file', metavar='FILE')
	parser.add_argument('--user', '-u', type=user_group_param, help='user and group', metavar='USER:GROUP')
	parser.add_argument('--version', '-v', action='version', version='%(prog)s ' + version)

	args = parser.parse_args()
	foreground = args.foreground and not args.background

	# Get default config
	computed_config = deepcopy(defaults.default_config)

	# Marge it with user config
	if args.config:
		yaml_config = yamlcfg.YAMLConfig(paths=[args.config])._data
	else:
		yaml_config = yamlcfg.YAMLConfig(paths=['winkle.yaml', '/etc/winkle/winkle.yaml'])._data
	mergedict(computed_config, yaml_config)

	# Merge it with config in configuration directory
	if computed_config['program']['config-dir']:
		path = Path(computed_config['program']['config-dir'])
		for file in sorted(path.glob('*.yaml')):
			yaml_config = yamlcfg.YAMLConfig(str(file))._data
			mergedict(computed_config, yaml_config)

	# Override config with command line options
	if args.pid_file:
		computed_config['program']['pid-file'] = args.pid_file
	if args.log_file:
		computed_config['program']['log-file'] = args.log_file
	if args.user:
		computed_config['program']['user'] = args.user[0]
		computed_config['program']['group'] = args.user[1]
	if foreground:
		computed_config['program']['foreground'] = foreground

	if args.install:
		daemon.install(computed_config)
		sys.exit()

	if computed_config['program']['user']:
		uidgid = daemon.get_ids(computed_config['program']['user'], computed_config['program']['group'])
		daemon.reduce_privileges(uidgid)

	defaults.log_config['handlers']['file']['filename'] = computed_config['program']['log-file']

	if computed_config['program']['foreground']:
		defaults.log_config['root']['handlers'] = ['console']
		run(computed_config)
	else:
		daemon.daemonize(computed_config['program']['pid-file'], run, computed_config)

def run(yamlconfig: Mapping[str, Any]) -> None:
	logging.config.dictConfig(defaults.log_config)
	log = logging.getLogger(__name__)
	log.info("Winkle %s by Derek Kulinski <derek.kulinski@openx.com>" % version)

	router = Router(yamlconfig)
	router.run()

if __name__ == '__main__':
	main()
