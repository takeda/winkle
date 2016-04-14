#! /usr/bin/env python

from setuptools import setup

setup(
	name = 'service-router',
	version = '0.1',
	install_requires = ['click ~= 6.6', 'aiohttp ~= 0.21.5', 'cachetools ~= 1.1.6', 'yamlcfg ~= 0.5.3'],
	entry_points = {
		'console_scripts': [
			'service-router = service_router.main:main'
		]
	},
	packages = ['service_router'],
	test_suite = 'tests',
	author = 'Derek Kulinski',
	author_email = 'takeda@takeda.tk'
)
