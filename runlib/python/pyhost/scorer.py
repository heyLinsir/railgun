#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# @file: runlib/python/pyhost/scorer.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# This file is released under BSD 2-clause license.

import re
import os
import pep8
import unittest
from time import time

from railgun.common.fileutil import dirtree
from railgun.common.lazy_i18n import lazy_gettext
from railgun.common.csvdata import CsvSchema
from .errors import ScorerFailure
from .utility import UnitTestScorerDetailResult, Pep8DetailReport
from coverage import coverage


class Scorer(object):
    """Base class for all scorers. All scorers should give a score between
    0 and 100."""

    def __init__(self, name):
        # name of the score
        self.name = name
        # time used by this module
        self.time = None
        # final score of the testing module
        self.score = None
        # brief explanation of the score
        self.brief = None
        # detail explanation of the score
        self.detail = None

    def _run(self):
        pass

    def run(self):
        """Run the testing module and generate the score. If a `ScorerFailure`
        is generated, the score will be set to 0.0."""
        try:
            startTime = time()
            self._run()
            self.time = time() - startTime
        except ScorerFailure, ex:
            self.brief = ex.brief
            self.detail = ex.detail
            self.score = ex.score


class UnitTestScorer(Scorer):
    """scorer according to the result of unit test"""

    def __init__(self, suite):
        super(UnitTestScorer, self).__init__(
            lazy_gettext('Functionality Scorer'))
        self.suite = suite

    def _run(self):
        # if self.suite is callable, then load the suite now
        # this is useful when dealing with student uploaded test case.
        if (callable(self.suite)):
            self.suite = self.suite()
        # get the result of unittest
        result = UnitTestScorerDetailResult()
        self.suite.run(result)
        # format score and reports according to unittest result
        total = self.suite.countTestCases()
        errors, failures = map(len, (result.errors, result.failures))
        # give out a score according to the above statistics
        success = total - (errors + failures)
        if (total > 0):
            self.score = 100.0 * success / total
        else:
            self.score = 100.0
        # format the brief report
        self.brief = lazy_gettext(
            '%(rate).2f%% tests (%(success)d out of %(total)d) passed',
            rate=self.score, total=total, time=self.time, success=success
        )
        # format the detailed report
        self.detail = result.details

    @staticmethod
    def FromTestCase(testcase):
        """Make a `UnitTestScorer` instance from `testcase`"""
        return UnitTestScorer(
            lambda: unittest.TestLoader().loadTestsFromTestCase(testcase))

    @staticmethod
    def FromNames(names):
        """Make a `UnitTestScorer` instance from test case `names`."""
        suite = lambda: unittest.TestLoader().loadTestsFromNames(names)
        return UnitTestScorer(suite)


class CodeStyleScorer(Scorer):
    """scorer according to the code style."""

    def __init__(self, filelist, skipfile=None):
        """Check the code style of `filelist`, skip if `skipfile(path)` is
        True."""

        super(CodeStyleScorer, self).__init__(lazy_gettext('CodeStyle Scorer'))
        skipfile = skipfile or (lambda path: False)
        is_pyfile = lambda p: (p[-3:].lower() == '.py')
        self.filelist = [p for p in filelist
                         if not skipfile(p) and is_pyfile(p)]

    def _run(self):
        guide = pep8.StyleGuide()
        guide.options.show_source = True
        guide.options.report = Pep8DetailReport(guide.options)
        result = guide.check_files(self.filelist)

        # the final score should be count_trouble_files() / total_file
        total_file = len(self.filelist)
        trouble_file = result.count_trouble_files()
        if (total_file > 0.0):
            self.score = 100.0 * (total_file - trouble_file) / total_file
        else:
            self.score = 100.0

        # format the brief report
        if (trouble_file > 0):
            self.brief = lazy_gettext(
                '%(rate).2f%% files (%(trouble)d out of %(total)d) did not '
                'pass PEP8 code style check',
                rate=100.0 - self.score, total=total_file, trouble=trouble_file
            )
        else:
            self.brief = lazy_gettext('All files passed PEP8 code style check')

        # format detailed reports
        self.detail = result.build_report()

    @staticmethod
    def FromHandinDir(ignore_files=None):
        """Create a `CodeStyleScorer` for all files under handin directory
        except `ignore_files`."""

        ignore_files = ignore_files or []
        if (isinstance(ignore_files, str) or isinstance(ignore_files, unicode)):
            ignore_files = [ignore_files]
        return CodeStyleScorer(dirtree('.'), (lambda p: p in ignore_files))


class CoverageScorer(Scorer):
    """scorer according to the result of coverage."""

    def __init__(self, suite, filelist):
        '''
        Run all test cases in `suite` and then get the coverage of all files
        in `filelist`.
        '''
        super(CoverageScorer, self).__init__(lazy_gettext('Coverage Scorer'))

        self.suite = suite
        self.brief = []
        self.filelist = filelist

    def _run(self):
        cov = coverage(branch=True)
        cov.start()

        # If self.suite is callable, generate test suite first
        if (callable(self.suite)):
            self.suite = self.suite()

        # Run the test suite
        # the `result` is now ignored, but we can get use of it if necessary
        result = UnitTestScorerDetailResult()
        self.suite.run(result)
        cov.stop()
        cov.xml_report(outfile='/tmp/hello.xml')

        # statement coverage rate
        total_exec = total_miss = 0
        total_branch = total_taken = total_partial = total_notaken = 0
        self.detail = []
        for filename in self.filelist:
            # get the analysis on given filename
            ana = cov._analyze(filename)
            # gather statement coverage on this file
            exec_stmt = set(ana.statements)
            miss_stmt = set(ana.missing)
            total_exec += len(exec_stmt)
            total_miss += len(miss_stmt)
            # gather branch coverage on this file
            # branch: {lineno: (total_exit, taken_exit)}
            branch = ana.branch_stats()
            file_branch = len(branch)
            file_taken = len([b for b in branch.itervalues() if b[0] == b[1]])
            file_notaken = len([b for b in branch.itervalues()
                                if b[0] != b[1] and b[1] == 0])
            file_partial = file_branch - file_taken - file_notaken
            # apply file branch to global
            total_branch += file_branch
            total_taken += file_taken
            total_partial += file_partial
            total_notaken += file_notaken

            # gather all source lines into detail report
            stmt_text = []
            branch_text = []
            with open(filename, 'rb') as fsrc:
                for i, s in enumerate(fsrc, 1):
                    # first, format statement cover report
                    if i in miss_stmt:
                        stmt_text.append('- %s' % s.rstrip())
                    elif i in exec_stmt:
                        stmt_text.append('+ %s' % s.rstrip())
                    else:
                        stmt_text.append('  %s' % s.rstrip())
                    # next, format branch cover report
                    branch_exec = branch.get(i, None)
                    if (not branch_exec):
                        branch_text.append('  %s' % s.rstrip())
                    elif (branch_exec[1] == branch_exec[0]):
                        # branch taken
                        branch_text.append('+ %s' % s.rstrip())
                    elif (branch_exec[1] == 0):
                        # branch not taken
                        branch_text.append('- %s' % s.rstrip())
                    else:
                        # branch partial taken
                        branch_text.append('* %s' % s.rstrip())
            # compose final detail
            stmt_text = '\n'.join(stmt_text)
            branch_text = '\n'.join(branch_text)

            # the statement coverage
            self.detail.append(lazy_gettext(
                '%(filename)s: %(miss)d statement(s) not covered.\n'
                '%(sep)s\n'
                '%(source)s',
                filename=filename, sep='-' * 70, miss=len(miss_stmt),
                source=stmt_text
            ))

            # the branch coverage
            self.detail.append(lazy_gettext(
                '%(filename)s: '
                '%(partial)d branch(es) partially taken and '
                '%(notaken)d branch(es) not taken.\n'
                '%(sep)s\n'
                '%(source)s',
                filename=filename, sep='-' * 70, miss=len(miss_stmt),
                source=branch_text, taken=file_taken, notaken=file_notaken,
                partial=file_partial
            ))

        def safe_divide(a, b):
            if (b > 0):
                return float(a) / float(b)
            return 0.0

        self.stmt_cover = 100.0 - 100.0 * safe_divide(total_miss, total_exec)
        self.branch_cover = 100.0 * safe_divide(total_taken, total_branch)
        self.branch_partial = 100.0 * safe_divide(total_partial, total_branch)

        # final score
        self.score = (
            self.stmt_cover * 0.5 +
            self.branch_cover * 0.5 +
            self.branch_partial * 0.25
        )
        self.brief = lazy_gettext(
            '%(stmt).2f%% statements covered, '
            '%(branch).2f%% branches taken and '
            '%(partial).2f%% partially taken.',
            stmt=self.stmt_cover,
            branch=self.branch_cover,
            partial=self.branch_partial,
        )

    @staticmethod
    def FromHandinDir(files_to_cover, test_pattern='test_.*\\.py$'):
        """Create a `CoverageScorer` to get score for all unit tests provided
        by students according to the coverage of files in `files_to_cover`.

        Only the files matching `test_pattern` will be regarded as unit test
        file.
        """

        p = re.compile(test_pattern)
        test_modules = []
        for f in dirtree('.'):
            fpath, fext = os.path.splitext(f)
            if (fext.lower() == '.py' and p.match(f)):
                test_modules.append(fpath.replace('/', '.'))

        suite = lambda: unittest.TestLoader().loadTestsFromNames(test_modules)
        return CoverageScorer(suite, files_to_cover)


class InputClassScorer(Scorer):
    """Scorer to the input data for BlackBox testing."""

    def __init__(self, schema, csvdata, check_classes=None):
        """Construct a new `InputClassScorer` on given `csvdata`, checked by
        rules defined in `check_classes`."""

        super(InputClassScorer, self).__init__(
            lazy_gettext('InputClass Scorer')
        )

        self.schema = schema
        self.csvdata = csvdata
        self.check_classes = check_classes or []

    def getDescription(self, check_class):
        """Get the description for given `check_class`."""

        if (hasattr(check_class, 'description')):
            return getattr(check_class, 'description')
        if (hasattr(check_class, '__name__')):
            return getattr(check_class, '__name__')
        return str(check_class)

    def rule(self, description):
        """Decorator to add given `method` into `check_classes`."""
        def outer(method):
            """Direct decorator on `method` which set method.description."""
            setattr(method, 'description', description)
            self.check_classes.append(method)
            return method
        return outer

    def _run(self):
        try:
            self.detail = []
            covered = set()
            for obj in CsvSchema.LoadCSV(self.schema, self.csvdata):
                # each record should be sent to all check classes, to see
                # what classes it covered
                for i, c in enumerate(self.check_classes):
                    if c(obj):
                        covered.add(i)
            # total up score by len(covered) / total_classes
            self.score = 100.0 * len(covered) / len(self.check_classes)
            self.brief = lazy_gettext(
                '%(rate).2f%% input classes (%(cover)s out of %(total)s) '
                'covered',
                cover=len(covered), total=len(self.check_classes),
                rate=self.score
            )
            # build more detailed report
            for i, c in enumerate(self.check_classes):
                if i in covered:
                    self.detail.append(lazy_gettext(
                        'COVERED: %(checker)s',
                        checker=self.getDescription(c)
                    ))
                else:
                    self.detail.append(lazy_gettext(
                        'NOT COVERED: %(checker)s',
                        checker=self.getDescription(c)
                    ))
        except KeyError, ex:
            raise ScorerFailure(
                brief=lazy_gettext('CSV data does not match schema.'),
                detail=[ex.args[0]]
            )
        except ValueError, ex:
            raise ScorerFailure(
                brief=lazy_gettext('CSV data does not match schema.'),
                detail=[ex.args[0]]
            )
