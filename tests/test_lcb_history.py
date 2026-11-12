import copy
import unittest
from scripts.verify_lcb_history import reference_score


class HistoricalCodingTests(unittest.TestCase):
    def setUp(self):
        self.questions=[{'platform':'synthetic','question_id':str(i),'question_content':'Synthetic',
                         'starter_code':''} for i in range(2)]
        self.rows=[{**q,'contest_date':'2025-03-01','graded_list':[True,False],'pass@1':0.5} for q in self.questions]

    def score(self):return reference_score(self.rows,self.questions,'2025-02-01','2025-05-01')

    def test_pass_at_one_is_mean_accuracy_not_best_of_many(self):
        self.assertEqual(self.score(),{'score':0.5,'samples_per_task':2})

    def test_mismatched_inputs_missing_tasks_and_wrong_grades_are_rejected(self):
        original=copy.deepcopy(self.rows)
        self.rows[0]['question_content']='Different revision'
        with self.assertRaises(ValueError):self.score()
        self.rows=copy.deepcopy(original);self.rows.pop()
        with self.assertRaises(ValueError):self.score()
        self.rows=copy.deepcopy(original);self.rows[0]['pass@1']=1
        with self.assertRaises(ValueError):self.score()
