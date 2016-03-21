import logging.config
from typing import Any, Mapping

import click
from yamlcfg import YamlConfig

from .router import Router

@click.command()
def main():
	config = YamlConfig("router.yaml")  # type: Mapping[str, Any]

	# Configure logging
	log_config = {
		'version': 1,
		'formatters': {
			'simple': {'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'}
		},
		'handlers': {
			'console': {
				'class': 'logging.StreamHandler',
				'formatter': 'simple',
				'stream': 'ext://sys.stdout'
			}
#			'file': {
#				'class': 'logging.handlers.TimedRotatingFileHandler',
#				'formatter': 'simple',
#				'filename': arguments['--log'],
#				'when': 'midnight',
#				'backupCount': 14,
#				'delay': True
#			}
		},
		'root': {
			'level': 'DEBUG',
			'handlers': ['console']
		},
		'loggers': {
			'service_router': {}
		}
	}
	logging.config.dictConfig(log_config)
	log = logging.getLogger(__name__)  # type: logging.Logger
	log.info("Starting service-router")

	router = Router(config)
	router.start()
