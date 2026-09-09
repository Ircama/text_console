#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legacy setup.py shim.

The packaging metadata has been moved to ``pyproject.toml`` (PEP 621).
This file is kept only for backwards compatibility with tools that
still invoke ``python setup.py``. All actual configuration now lives
in ``pyproject.toml``.
"""

from setuptools import setup

setup()
