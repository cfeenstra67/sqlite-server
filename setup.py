from distutils.core import setup

setup(
	name='sqlite-server',
	version='1.0',
	description='Simple sqlite database server using twisted',
	author='Cam Feenstra',
	author_email='cameron.l.feenstra@gmail.com',
	packages=['sqlite-server'],
	install_requires=['Twisted', 'pandas']
)