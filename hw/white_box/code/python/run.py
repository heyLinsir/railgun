#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# @file: hw/chkpath/code/python/run.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# This file is released under BSD 2-clause license.

from pyhost.scorer import CodeStyleScorer, CoverageScorer
from pyhost import SafeRunner


if (__name__ == '__main__'):
    scorers = [
        (CodeStyleScorer.FromHandinDir('run.py'), 0.1),
        (CoverageScorer.FromHandinDir(['myfunc.py']), 0.9),
    ]
    SafeRunner.run(scorers)
