default_config = {
	'program': {
		'services-config': '/etc/winkle/services.yaml',
		'config-dir': None,
		'rack': None,
		'user': 'nobody',
		'group': 'nobody',
		'log-file': '/var/log/winkle/winkle.log',
		'pid-file': '/var/run/winkle/winkle.pid'
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
				'status': 'sudo service haproxy status',
				'start': 'sudo service haproxy start',
				'reload': 'sudo service haproxy reload',
				'pid-file': '/var/run/haproxy.pid',
				'state-file': '/var/run/winkle/haproxy.state',
				'socket': '/var/lib/haproxy/haproxy.sock',
				'check-config': '/usr/sbin/haproxy -c -f {config}'
			},
			'global': [
				'stats socket /var/lib/haproxy/haproxy.sock mode 660 level admin',
				'server-state-file /var/run/winkle/haproxy.state'
			],
			'defaults': [
				'retries 3',
				'timeout connect 5s',
				'timeout client 10m',
				'timeout server 10m',
				'load-server-state-from-file global'
			],
			'services': [],
			'extra': []
		}
	}
}

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
		'handlers': ['file']
	},
	'loggers': {
		'winkle': {},
		'asyncio': {}
	}
}
