import unittest
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.gpqa_diamond import private_path, read_completion, request_completion, summarize, tasks


class GPQADiamondTests(unittest.TestCase):
    def test_admission_retry_honors_server_delay(self):
        response=io.BytesIO(b'{"choices":[]}')
        response.headers={'Content-Type':'application/json'}
        outcomes=[HTTPError('http://example.invalid',429,'busy',{'Retry-After':'7'},None),response]
        class Opener:
            def open(self, request, timeout):
                outcome=outcomes.pop(0)
                if isinstance(outcome,Exception):raise outcome
                return outcome
        with patch('scripts.gpqa_diamond.time.sleep') as sleep:
            result=request_completion(Opener(),object())
        sleep.assert_called_once_with(7.0)
        self.assertEqual(result['transport_attempts'],2)

    def test_invalid_request_is_not_retried(self):
        class Opener:
            def open(self, request, timeout):
                raise HTTPError('http://example.invalid',400,'bad request',{},None)
        with patch('scripts.gpqa_diamond.time.sleep') as sleep:
            with self.assertRaises(HTTPError):request_completion(Opener(),object())
        sleep.assert_not_called()

    def test_stream_keeps_reasoning_out_of_final_answer(self):
        events = [
            {'model': 'test-model', 'choices': [{'delta': {'reasoning_content': 'Answer: B is tempting.'}}]},
            {'choices': [{'delta': {'content': 'Answer: A'}, 'finish_reason': 'stop'}]},
            {'choices': [], 'usage': {'completion_tokens': 12}, 'timings': {'predicted_ms': 25}},
        ]
        stream = io.BytesIO(b''.join(b'data: ' + json.dumps(event).encode() + b'\n\n' for event in events) + b'data: [DONE]\n')
        stream.headers = {'Content-Type': 'text/event-stream', 'x-litellm-model-id': 'synthetic-route'}
        result = read_completion(stream)
        self.assertEqual(result['choices'][0]['message']['content'], 'Answer: A')
        self.assertEqual(result['usage']['completion_tokens'], 12)
        self.assertEqual(result['model'], 'test-model')
        self.assertEqual(result['timings']['predicted_ms'], 25)
        self.assertEqual(result['gateway_headers']['x-litellm-model-id'], 'synthetic-route')

    def test_model_switch_inside_stream_is_not_scored(self):
        events = [{'model': 'one', 'choices': []},
                  {'model': 'two', 'choices': [{'delta': {'content': 'Answer: A'}, 'finish_reason': 'stop'}]}]
        stream = io.BytesIO(b''.join(b'data: ' + json.dumps(event).encode() + b'\n' for event in events))
        stream.headers = {'Content-Type': 'text/event-stream'}
        with self.assertRaises(ValueError):
            read_completion(stream)

    def test_incomplete_stream_is_not_a_model_failure(self):
        stream = io.BytesIO(b'data: {"choices":[{"delta":{"content":"Answer: A"}}]}\n')
        stream.headers = {'Content-Type': 'text/event-stream'}
        with self.assertRaises(ValueError):
            read_completion(stream)

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
