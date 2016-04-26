import logging.config
from typing import Any, Mapping

import click
import yamlcfg

from winkle import daemon, defaults
from winkle.router import Router

@click.command()
@click.option('--foreground/--background', '-f', default=False, help='Run in foreground and log to console')
@click.option('--config', '-c', type=str, default='winkle.yaml', help='Configuration file')
@click.option('--pid-file', '-p', type=str, default='router.pid', help='PID file')
@click.version_option()
def main(foreground: bool, config: str, pid_file: str):
	# noinspection PyProtectedMember
	yamlconfig = yamlcfg.YamlConfig(config)._data  # type: Mapping[str, Any]

	if not foreground:
		defaults.log_config['root']['handlers'] = ['file']

	if foreground:
		run(yamlconfig)
	else:
		daemon.daemonize(pid_file, run, yamlconfig)

def run(yamlconfig: Mapping[str, Any]) -> None:
	logging.config.dictConfig(defaults.log_config)
	log = logging.getLogger(__name__)
	log.info("Winkle by Derek Kulinski <derek.kulinski@openx.com>")

	router = Router(yamlconfig)
	router.run()

if __name__ == '__main__':
	main()
