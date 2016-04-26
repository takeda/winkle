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
		},
		'file': {
			'class': 'logging.handlers.TimedRotatingFileHandler',
			'formatter': 'simple',
			'filename': 'winkle.log',
			'when': 'midnight',
			'backupCount': 14,
			'delay': True
		}
	},
	'root': {
		'level': 'DEBUG',
		'handlers': ['console']
	},
	'loggers': {
		'winkle': {},
		'asyncio': {}
	}
}

default_config = {
	'program': {
		'services-config': 'services.yaml',
		'rack': None
	},
	'sources': {
		'consul': {
			'host': '127.0.0.1',
			'port': 8500,
			'consistency': 'stale'
		}
	},
	'sinks': {
		'haproxy': {
			'service': {
				'config': '/etc/haproxy/haproxy.cfg',
				'status': 'service haproxy status',
				'start': 'service haproxy start',
				'reload': 'service haproxy reload'
			}
		}
	}
}
