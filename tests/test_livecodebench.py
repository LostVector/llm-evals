import unittest

from scripts.livecodebench import scorer_infrastructure_error


class CodingScorerTests(unittest.TestCase):
    def test_runner_failure_is_distinct_from_wrong_answer(self):
        self.assertTrue(scorer_infrastructure_error([['{"error_code":-5,"error_message":"TestRunnerError"}']]))
        self.assertFalse(scorer_infrastructure_error([['{"error_code":-2,"error_message":"Wrong Answer"}']]))
        self.assertFalse(scorer_infrastructure_error([['{"error_code":-3,"error_message":"Time Limit Exceeded"}']]))
        self.assertFalse(scorer_infrastructure_error([['{}']]))
