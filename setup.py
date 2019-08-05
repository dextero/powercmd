from setuptools import setup

setup(name='powercmd',
      version='0.3',
      description='A generic framework to build typesafe line-oriented command interpreters',
      url='http://github.com/dextero/powercmd',
      author='Marcin Radomski',
      author_email='marcin@mradomski.pl',
      license='MIT',
      packages=['powercmd'],
      zip_safe=True,
      install_reqiures=['prompt_toolkit >= 2.0'])
