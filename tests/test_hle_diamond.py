from pathlib import Path
import unittest

from scripts.hle_diamond import PROTOCOL, judge_payload, messages, private_run_path, run_prediction, select_questions, summarize, validate_endpoint, validate_judgment, validate_questions


def question(id='synthetic-1',image=''):
    return dict(id=id,question='Synthetic test prompt, not benchmark content.',answer='synthetic gold',image=image,partition='reasoning')


def config():
    return dict(model='synthetic-local',input_mode='text-input-full',temperature=0,max_tokens=8192,token_parameter='max_tokens',seed=7,reasoning_effort=None,limit=2)


def grade(correct='yes'):
    return dict(status='graded',judgment=dict(correct=correct,strict=True,confidence=80,reasoning='Synthetic fixture.',extracted_final_answer='fixture'))


class HLETests(unittest.TestCase):
    def test_inputs_do_not_include_gold(self):
        q=question(image='data:image/png;base64,synthetic')
        self.assertNotIn(q['answer'],str(messages(q,'system','multimodal')))
        self.assertEqual(len(messages(q,'system','multimodal')[1]['content']),2)
        self.assertEqual(len(messages(q,'system','text-input-full')[1]['content']),1)
        self.assertEqual(select_questions([q,question('synthetic-2')],'text-only-subset')[0]['id'],'synthetic-2')

    def test_attempts_have_fixed_settings_and_no_tools(self):
        requests=[]
        def fake(body):
            requests.append(body)
            return dict(choices=[dict(message={'content':'synthetic response'},finish_reason='stop')])
        result=run_prediction([question()],'system',config(),fake)
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0]['temperature'],0)
        self.assertEqual(requests[0]['max_tokens'],8192)
        self.assertNotIn('tools',requests[0])
        self.assertEqual(result['synthetic-1']['status'],'answered')

    def test_generation_failure_stays_in_denominator(self):
        q1,q2=question(),question('synthetic-2')
        def fake(body):raise TimeoutError()
        failed=run_prediction([q2],'system',config(),fake)
        predictions={'synthetic-1':dict(status='answered',response='fixture'),**failed}
        manifest=dict(task_ids=[q1['id'],q2['id']],partitions={q1['id']:'reasoning',q2['id']:'knowledge'},config=config())
        summary=summarize(manifest,predictions,{'synthetic-1':grade()})
        self.assertEqual(summary['overall']['n'],2)
        self.assertEqual(summary['overall']['accuracy_percent'],50)
        self.assertEqual(summary['generation_errors'],1)
        self.assertEqual(summary['partitions']['knowledge']['accuracy_percent'],0)

    def test_judge_failure_prevents_reporting(self):
        manifest=dict(task_ids=['synthetic-1'],partitions={'synthetic-1':'reasoning'},config=config())
        predictions={'synthetic-1':dict(status='answered',response='fixture')}
        for judgments in ({},{'synthetic-1':dict(status='judge_error')}):
            with self.assertRaises(ValueError):summarize(manifest,predictions,judgments)
        with self.assertRaises(ValueError):summarize(manifest,{}, {})

    def test_subset_is_not_labeled_full(self):
        c=config();c['limit']=5
        manifest=dict(task_ids=['synthetic-1'],partitions={'synthetic-1':'reasoning'},config=c)
        predictions={'synthetic-1':dict(status='generation_error')}
        self.assertEqual(summarize(manifest,predictions,{})['task_set'],'development-subset')
        c['limit']=None;c['input_mode']='text-only-subset'
        with self.assertRaises(ValueError):summarize(manifest,predictions,{})
        c['input_mode']='text-input-full'
        with self.assertRaises(ValueError):summarize(manifest,predictions,{})

    def test_judge_uses_gold_but_validates_output(self):
        prompt='{question} / {correct_answer} / {response}'
        body=judge_payload(question(),{'response':'fixture'},prompt,'synthetic-judge','medium')
        self.assertIn('synthetic gold',str(body['messages']))
        self.assertEqual(body['reasoning_effort'],'medium')
        self.assertEqual(body['response_format']['type'],'json_schema')
        self.assertEqual(validate_judgment(grade()['judgment'])['correct'],'yes')
        for value in ({},{'correct':'maybe'},dict(grade()['judgment'],confidence=True),dict(grade()['judgment'],strict=False)):
            with self.assertRaises(ValueError):validate_judgment(value)

    def test_dataset_must_match_pinned_shape(self):
        with self.assertRaises(ValueError):validate_questions([question()])
        questions=[question(f'synthetic-{i}',image='image' if i<272 else '') for i in range(1000)]
        for i,q in enumerate(questions):q['partition']='reasoning' if i<500 else 'knowledge'
        validate_questions(questions)
        questions[0]['id']=questions[1]['id']
        with self.assertRaises(ValueError):validate_questions(questions)

    def test_endpoint_and_artifact_boundaries(self):
        self.assertEqual(validate_endpoint('http://localhost:8080/v1'),'http://localhost:8080/v1/chat/completions')
        for url in ('file:///tmp/data','https://secret@example.org/v1','https://example.org/v1?key=secret'):
            with self.assertRaises(ValueError):validate_endpoint(url)
        with self.assertRaises(ValueError):private_run_path(Path('data/results/raw-output'))
        self.assertEqual(len(PROTOCOL['dataset_revision']),40)
        self.assertEqual(len(PROTOCOL['evaluator_revision']),40)


if __name__=='__main__':unittest.main()
