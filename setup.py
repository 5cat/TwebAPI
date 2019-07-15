from setuptools import setup
from setuptools import find_packages

long_description = '''
TwebAPI is a library that help you manage your twitter account
without the use of the offical twitter api, instead it uses
the backend requests that the broweser uses.

TwebAPI is compatible with only with Python>=3.5
and is distributed under the MIT license.
'''

setup(name='TwebAPI',
	  version='0.0.1',
	  description='twitter api',
	  long_description=long_description,
	  author='Hashim Almutairi',
	  author_email='Me@Hashim.iD',
	  url='https://github.com/HashimHL/TwebAPI',
	  #download_url='https://github.com/keras-team/keras/tarball/2.2.4',
	  license='MIT',
	  install_requires=['numpy>=1.9.1',
	  					'tqdm'],
	  classifiers=[
		  'Intended Audience :: Developers',
		  'Intended Audience :: Education',
		  'Intended Audience :: Science/Research',
		  'License :: OSI Approved :: MIT License',
		  'Programming Language :: Python :: 3',
		  'Programming Language :: Python :: 3.6',
		  'Topic :: Software Development :: Libraries',
		  'Topic :: Software Development :: Libraries :: Python Modules'
	  ],
	  packages=find_packages())