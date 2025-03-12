from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

from pick_stream import __version__ as version

setup(
	name = 'pick_stream',
	version = version,
	description = 'A robust, efficient, and accurate inventory management module that simplifies the replenishment process, reduces errors, and enhances operational efficiency across stores.',
	author = 'Jollys Pharmacy Limited',
	author_email = 'cdgrant@jollysonline.com',
	packages = find_packages(),
	zip_safe = False,
	include_package_data = True,
	install_requires = install_requires
)
