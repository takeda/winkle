#! /usr/bin/env python

from setuptools import setup

setup(
	name = 'service-router',
	version = '0.1',
	install_requires = ['click', 'python-consul[asyncio]', 'cachetools'],
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
