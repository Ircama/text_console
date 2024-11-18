#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import re
import os
import sys

import json
from urllib import request
from pkg_resources import parse_version

###########################################################################

END_OF_INTRODUCTION = '## Installation'

EPILOGUE = '''
Full information and usage details at the [text_console GitHub repository](https://github.com/Ircama/text_console).
'''

DESCRIPTION = (
        "A customizable Tkinter-based text console widget,"
        " in which a user types in commands"
        " to be sent to the Python interpreter."
    ),

PACKAGE_NAME = "text_console"

VERSIONFILE = "text_console/__version__.py"

###########################################################################

def versions(pkg_name, site):
    url = 'https://' + site + '.python.org/pypi/' + pkg_name + '/json'
    try:
        releases = json.loads(request.urlopen(url).read())['releases']
    except Exception as e:
        print("Error while getting data from URL '" + url + "': " + e)
        return []
    return sorted(releases, key=parse_version, reverse=True)

with open("README.md", "r") as readme:
    long_description = readme.read()

build = ''
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

if os.environ.get('GITHUB_RUN_NUMBER') is not None:
    try:
        version_list_pypi = [
            a for a in versions(PACKAGE_NAME, 'pypi') if a.startswith(verstr)]
        version_list_testpypi = [
            a for a in versions(PACKAGE_NAME, 'testpypi') if a.startswith(verstr)]
        if (version_list_pypi or
                version_list_testpypi or
                os.environ.get('GITHUB_FORCE_RUN_NUMBER') is not None):
            print('---------------------------------'
                '---------------------------------')
            print("Using build number " + os.environ['GITHUB_RUN_NUMBER'])
            if version_list_pypi:
                print(
                    "Version list available in pypi: " +
                    ', '.join(version_list_pypi))
            if version_list_testpypi:
                print(
                    "Version list available in testpypi: " +
                    ', '.join(version_list_testpypi))
            print('---------------------------------'
                '---------------------------------')
            verstr += '-' + os.environ['GITHUB_RUN_NUMBER']
    except Exception as e:
        print("Cannot use pypi or testpypi for getting the version:", e)
        

setup(
    name=PACKAGE_NAME,
    version=verstr,
    description=(DESCRIPTION),
    long_description=long_description[
        :long_description.find(END_OF_INTRODUCTION)] + EPILOGUE,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: European Union Public Licence 1.2 (EUPL 1.2)",
        "Topic :: Software Development :: Libraries :: Python Modules",
        'Programming Language :: Python :: 3 :: Only',
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
    ],
    keywords=("shell console tkinter"),
    author="Ircama",
    url="https://github.com/Ircama/text_console",
    license='EUPL-1.2',
    packages=find_packages(),
    entry_points={
    'console_scripts': [
        'text_console = text_console.__main__:main',
    ]},
    python_requires='>3.6'
)
