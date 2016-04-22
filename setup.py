#! /usr/bin/env python

from setuptools import setup

setup(
	name = 'winkle',
	version = '0.1',
	install_requires = ['click ~= 6.6', 'aiohttp ~= 0.21.5', 'cachetools ~= 1.1.6', 'yamlcfg ~= 0.5.3'],
	entry_points = {
		'console_scripts': [
			'winkle = winkle.main:main'
		]
	},
	packages = ['winkle'],
	test_suite = 'tests',
	author = 'Derek Kulinski',
	author_email = 'takeda@takeda.tk'
)
