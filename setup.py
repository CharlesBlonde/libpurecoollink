#!/usr/bin/env python3
from setuptools import setup, find_packages

PACKAGES = find_packages(exclude=['tests', 'tests.*'])

REQUIRES = [
    'requests>=2,<3',
    'netifaces',
    'six',
    'paho_mqtt',
    'pycryptodome'
]

PROJECT_CLASSIFIERS = [
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.4',
    'Topic :: Software Development :: Libraries'
]

setup(
    name="libpurecoollink",
    version="0.4.1",
    license="Apache License 2.0",
    url="http://libpurecoollink.readthedocs.io",
    download_url="https://github.com/CharlesBlonde/libpurecoollink",
    author="Charles Blonde",
    author_email="charles.blonde@gmail.com",
    description="Dyson Pure Cool/Hot+Cool Link and 360 eye robot "
                "vacuum devices Python library",
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=True,
    platforms='any',
    install_requires=REQUIRES,
    test_suite='tests',
    keywords=['dyson', 'purecoollink', 'eye360', 'purehotcoollink'],
    classifiers=PROJECT_CLASSIFIERS,
)
