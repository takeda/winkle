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
		},
		'simplefile': {
			'class': 'logging.FileHandler',
			'formatter': 'simple',
			'filename': 'log',
			'mode': 'w',
			'delay': False
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
