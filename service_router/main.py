import logging.config
from typing import Any, Mapping

import click
import yamlcfg

from service_router import daemon, defaults
from service_router.router import Router

@click.command()
@click.option('--foreground/--background', '-f', default=False, help='Run in foreground and log to console')
@click.option('--config', '-c', type=str, default='router.yaml', help='Configuration file')
@click.option('--pid-file', '-p', type=str, default='router.pid', help='PID file')
@click.version_option()
def main(foreground, config, pid_file):
	yamlconfig = yamlcfg.YamlConfig(config)._data  # type: Mapping[str, Any]

	if not foreground:
		defaults.log_config['root']['handlers'] = ['simplefile']

	logging.config.dictConfig(defaults.log_config)
	log = logging.getLogger(__name__)  # type: logging.Logger

	if foreground:
		run(log, yamlconfig)
	else:
		daemon.daemonize(pid_file, run, log, yamlconfig)

def run(log: logging.Logger, yamlconfig: Mapping[str, Any]):
	log.info("Starting service-router by Derek Kulinski <derek.kulinski@openx.com>")

	router = Router(yamlconfig)
	router.start()

if __name__ == '__main__':
	main()
