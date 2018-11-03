import re

from setuptools import setup


version = None
for line in open('./scdl/__init__.py'):
    m = re.search('__version__\s*=\s*(.*)', line)
    if m:
        version = m.group(1).strip()[1:-1]  # quotes
        break
assert version

setup(
    name='scdl',
    version=version,
    description='A friendly downloader library for the Soundcloud',
    author='SoundCloud',
    url='https://github.com/soundcloud/soundcloud-python',
    packages=['scdl'],
    include_package_data=True,
    package_data={
        '': ['README.rst']
    },
    install_requires=[
        'xmltodict',
        'python-dateutil',
        'requests',
        'demjson',
        'requests',
    ]
)