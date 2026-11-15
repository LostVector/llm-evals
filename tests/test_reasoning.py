import unittest
from scripts.reasoning import reasoning_policy


class ReasoningTests(unittest.TestCase):
    def test_unknown_is_not_unlimited(self):
        self.assertIsNone(reasoning_policy()['budget_tokens'])
        self.assertEqual(reasoning_policy({'budget_tokens': -1})['budget_tokens'], -1)

    def test_reject_private_or_invalid_metadata(self):
        for value in ({'api_key': 'secret'}, {'budget_tokens': True},
                      {'budget_tokens': -2}, {'parser': 'http://private'},
                      {'budget_exhaustion': 'pretend-supported'}):
            with self.assertRaises(ValueError):
                reasoning_policy(value)

    def test_request_budget_must_match_policy(self):
        from scripts.reasoning import request_parameters
        self.assertEqual(request_parameters({}), {})
        config={'reasoning':{'budget_tokens':27853},
                'reasoning_request':{'reasoning_budget_tokens':27853}}
        self.assertEqual(request_parameters(config),{'reasoning_budget_tokens':27853})
        config['reasoning_request']['reasoning_budget_tokens']=24576
        with self.assertRaises(ValueError):request_parameters(config)
        with self.assertRaises(ValueError):request_parameters({'reasoning_request':{'api_key':'secret'}})
