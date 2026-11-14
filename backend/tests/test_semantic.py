"""Optional tests with real model weights: NYAYA_TEST_SEMANTIC=1 python -m unittest discover -s backend/tests."""
from dataclasses import replace
import os
import json
from pathlib import Path
import tempfile
import unittest

from backend.config import Settings
from backend.rag import Pipeline
from backend.retrieval import Retriever


@unittest.skipUnless(os.getenv("NYAYA_TEST_SEMANTIC") == "1", "Set NYAYA_TEST_SEMANTIC=1 to download/use real BGE weights")
class SemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.settings = replace(Settings(), index_dir=Path(cls.temp.name))
        cls.index = Retriever(cls.settings)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_model_dimensions_and_paraphrase_retrieval(self):
        self.assertEqual(self.index.vectors.shape[1], 384)
        result = Pipeline(self.index, self.settings).retrieve('The shop delivered a broken appliance and refuses to return my payment. Where can I complain?')
        self.assertEqual(result['topic'], 'consumer')
        self.assertIn('consumer-route', {h['factId'] for h in result['retrieval']['chunks']})

    def test_unrelated_questions_abstain(self):
        pipeline = Pipeline(self.index, self.settings)
        for q in ['Who won a cricket match?', 'How do I grow tomatoes?', 'How do I file income tax?']:
            self.assertIsNone(pipeline.retrieve(q)['topic'])

    def test_expanded_regressions_with_real_embeddings(self):
        # No LLM or credentials: fail CI on wrong routes or missing expected facts.
        cases = json.loads((Path(__file__).parents[1] / 'eval_cases.json').read_text())
        pipeline = Pipeline(self.index, self.settings)
        for case in cases:
            with self.subTest(question=case['question']):
                answer = pipeline.retrieve(case['question'], case.get('previousTopic'))
                self.assertEqual(answer['topic'], case['topic'])
                if case.get('fact') and answer['topic'] != 'emergency':
                    self.assertIn(case['fact'], {c['factId'] for c in answer['retrieval']['chunks']})
