#!/usr/bin/env python3
from setuptools import setup, find_packages

PACKAGES = find_packages(exclude=['tests', 'tests.*'])

REQUIRES = [
    'requests>=2,<3',
    'enum34>=1.1.6',
    'netifaces',
    'six',
    'paho_mqtt',
    'pycryptodome'
]

PROJECT_CLASSIFIERS = [
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3.4',
    'Topic :: Software Development :: Libraries'
]

setup(
    name="libpurecoollink",
    version="0.2.0",
    license="Apache License 2.0",
    url="https://github.com/CharlesBlonde/libpurecoollink",
    download_url="https://github.com/CharlesBlonde/libpurecoollink",
    author="Charles Blonde",
    author_email="charles.blonde@gmail.com",
    description="Dyson Pure Cool Link Python library",
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=True,
    platforms='any',
    install_requires=REQUIRES,
    test_suite='tests',
    keywords=['dyson', 'purecoollink'],
    classifiers=PROJECT_CLASSIFIERS,
)
