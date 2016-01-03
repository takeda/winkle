import logging.config

import click

from .router import Router

from pprint import pprint as pp

def update(services):
	print("Change detected!")
	pp(services)


@click.command()
def main():
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
	log = logging.getLogger(__name__)

	callbacks = {
		'update': update
	}
	router = Router()
	router.start()
