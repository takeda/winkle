#! /usr/bin/env python

import os
from setuptools import setup
from winkle.version import version

def go_version(v):
	if 'GO_PIPELINE_LABEL' in os.environ:
		go_v = os.environ['GO_PIPELINE_LABEL'].split('.')
		return '%s+%s.%s' % (v, go_v[0], go_v[1])

	return v

setup(
	name = 'winkle',
	version = go_version(version),
	install_requires = ['aiohttp ~= 3.0.1', 'yamlcfg ~= 0.5.3'],
	entry_points = {
		'console_scripts': [
			'winkle = winkle.main:main'
		]
	},
	packages = ['winkle'],
	package_data = {
		'winkle': ['files/*.in']
	},
	test_suite = 'tests',
	author = 'Derek Kulinski',
	author_email = 'derek.kulinski@openx.com',
	url = 'https://github.corp.openx.com/black/winkle'
)
