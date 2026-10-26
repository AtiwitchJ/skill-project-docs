"""Intentional failures for demonstrating report evidence; not production defects.

Only run explicitly with --pattern fixture_cases.py. No external services.
"""
import unittest


class PassingExample(unittest.TestCase):
    def test_valid_result(self):self.assertEqual(2+2,4)


class AssertionExample(unittest.TestCase):
    def test_expected_mismatch(self):self.assertEqual(2+2,5,'Intentional assertion fixture')


class SetupExample(unittest.TestCase):
    def setUp(self):raise RuntimeError('Intentional setup fixture')
    def test_not_reached(self):self.fail('This body must not execute')


class TeardownExample(unittest.TestCase):
    def test_body_passes(self):self.assertTrue(True)
    def tearDown(self):raise RuntimeError('Intentional teardown fixture')


class CleanupExample(unittest.TestCase):
    def test_cleanup_is_observed(self):self.addCleanup(self.cleanup_failure)
    def cleanup_failure(self):raise RuntimeError('Intentional cleanup fixture')


class FixtureExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):raise RuntimeError('Intentional class fixture failure')
    def test_not_reached(self):pass


class SkippedExample(unittest.TestCase):
    @unittest.skip('Intentional skipped fixture')
    def test_skipped(self):pass


class SubtestExample(unittest.TestCase):
    def test_subtests(self):
        for value in (0,1):
            with self.subTest(value=value):self.assertEqual(value,0,'Intentional subtest fixture')
