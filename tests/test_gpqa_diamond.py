import unittest

from scripts.gpqa_diamond import private_path, summarize, tasks


class GPQADiamondTests(unittest.TestCase):
    def test_choice_shuffle_preserves_correct_answers(self):
        rows = [{'Record ID': str(i), 'High-level domain': 'synthetic', 'Question': 'Synthetic task',
                 'Correct Answer': 'correct', 'Incorrect Answer 1': 'wrong1',
                 'Incorrect Answer 2': 'wrong2', 'Incorrect Answer 3': 'wrong3'} for i in range(12)]
        protocol = {'expected_tasks': 12, 'answer_shuffle_seed': 0,
                    'prompt': '{Question}\nA) {A}\nB) {B}\nC) {C}\nD) {D}'}
        generated = tasks(rows, protocol)
        self.assertEqual(generated, tasks(rows, protocol))
        self.assertGreater(len({t['expected'] for t in generated}), 1)
        for task in generated:
            self.assertIn(task['expected'] + ') correct', task['prompt'])
        with self.assertRaises(ValueError):
            tasks(rows[:-1], protocol)
        rows[1]['Record ID'] = rows[0]['Record ID']
        with self.assertRaises(ValueError):
            tasks(rows, protocol)

    def test_summary_exposes_incomplete_and_failed_outputs(self):
        records = [{'correct': True, 'answer': 'A', 'seconds': 2, 'finish_reason': 'stop', 'response': {}},
                   {'correct': False, 'answer': None, 'seconds': 3, 'finish_reason': 'length',
                    'response': {'usage': {'completion_tokens_details': {'reasoning_closed_by': 'answer_room'}}}}]
        result = summarize(records, 198)
        self.assertEqual((result['completed'], result['total'], result['accuracy']), (2, 198, 0.5))
        self.assertEqual((result['unparsed'], result['truncated'], result['forced_reasoning_closures']), (1, 1, 1))
        self.assertAlmostEqual(result['wilson_95'][0], 0.09453120573423074)
        self.assertAlmostEqual(result['wilson_95'][1], 0.9054687942657693)

    def test_private_paths_cannot_escape_ignored_storage(self):
        with self.assertRaises(ValueError):
            private_path('data/results/raw-response.json')
        with self.assertRaises(ValueError):
            private_path('.local/../data/raw.json')


if __name__ == '__main__':
    unittest.main()
