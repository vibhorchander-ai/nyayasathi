"""Regression coverage for the speech/RTI confusion and constitutional boundaries."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

import httpx
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.corpus import load_corpus
from backend.main import ChatRequest, create_app
from backend.rag import Pipeline
from backend.retrieval import Retriever


class ConstitutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(engine='tfidf', index_dir=Path(self.temp.name) / 'index')
        self.index = Retriever(self.settings)
        self.pipeline = Pipeline(self.index, self.settings)

    def tearDown(self):
        self.temp.cleanup()

    def test_speech_question_retrieves_right_and_restrictions_not_rti(self):
        for q in ['what is a right to speech?', 'What is freedom of expression?', 'Is freedom of speech absolute?']:
            with self.subTest(q=q):
                answer = self.pipeline.retrieve(q, 'rti')
                self.assertEqual(answer['topic'], 'speech')
                chunks = answer['retrieval']['chunks']
                self.assertEqual(chunks[0]['factId'], 'speech-right')
                self.assertEqual({c['factId'] for c in chunks}, {'speech-right', 'speech-limits'})
                text = ' '.join(p['text'] for p in answer['points'])
                for term in ['19(1)(a)', 'citizens', '19(2)', 'reasonable', 'defamation']:
                    self.assertIn(term, text)
                self.assertNotIn('rti', {s['id'] for s in answer['sources']})

    def test_article_routing_distinguishes_21_from_21a(self):
        for article, topic in [('14', 'equality'), ('19 (1) (a)', 'speech'), ('19(2)', 'speech'),
                               ('21', 'liberty'), ('21A', 'education'), ('32', 'remedies')]:
            self.assertEqual(self.pipeline.retrieve(f'Explain Article {article}')['topic'], topic)
        for q in ['Explain Article 20', 'Explain Article 19(1)(b)', 'Compare Article 14 and Article 21']:
            self.assertEqual(self.pipeline.retrieve(q)['mode'], 'limited')

    def test_generic_rights_words_do_not_imply_coverage(self):
        for q in ['What is a right triangle?', 'Do animals have rights?', 'What is the right to property?',
                  'What is the right to vote?', 'What is freedom of assembly?', 'What are my rights?',
                  'What is the right to privacy?', 'What rights do I have when arrested?']:
            self.assertEqual(self.pipeline.retrieve(q, 'rti')['mode'], 'limited', q)

    def test_removing_speech_notes_abstains_instead_of_routing_to_rti(self):
        catalog = json.loads(self.settings.corpus_path.read_text())
        catalog['topics'] = [t for t in catalog['topics'] if not t.get('articles')]
        path = Path(self.temp.name) / 'old-corpus.json'
        path.write_text(json.dumps(catalog))
        settings = replace(self.settings, corpus_path=path)
        pipeline = Pipeline(Retriever(settings), settings)
        self.assertEqual(pipeline.retrieve('what is a right to speech?')['mode'], 'limited')

    def test_required_context_references_are_validated(self):
        catalog = json.loads(self.settings.corpus_path.read_text())
        catalog['topics'][0]['requiredFacts'] = ['missing-fact']
        path = Path(self.temp.name) / 'invalid-corpus.json'
        path.write_text(json.dumps(catalog))
        with self.assertRaisesRegex(ValueError, 'Required context'):
            load_corpus(path)

    def test_speech_generation_receives_both_qualifications_and_validates_citations(self):
        async def run():
            def provider(request):
                data = json.loads(request.content)
                notes = json.loads(data['messages'][1]['content'])['notes']
                self.assertEqual(len(notes), 2)
                self.assertTrue(any('19(2)' in n['text'] and 'defamation' in n['text'] for n in notes))
                self.assertTrue(any('citizens' in n['text'] for n in notes))
                claims = [{'text': n['text'], 'evidence': [{'chunk_id': n['chunk_id'], 'quote': n['text']}]} for n in notes]
                return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'insufficient_evidence': False, 'claims': claims})}}]})
            pipeline = Pipeline(self.index, replace(self.settings, groq_key='test-only'))
            async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
                return await pipeline.answer(ChatRequest(question='what is a right to speech?', useAI=True), client)
        result = asyncio.run(run())
        self.assertEqual(result['mode'], 'rag')
        self.assertEqual(len(result['points']), 2)

    def test_http_contract_exposes_updated_scope_and_speech_evidence(self):
        with TestClient(create_app(self.settings, self.index)) as client:
            status = client.get('/api/status').json()
            self.assertEqual(status['coverage'], len(self.index.catalog['topics']) - 1)
            self.assertEqual(status['chunks'], len(self.index.chunks))
            response = client.post('/api/chat', json={'question': 'what is a right to speech?', 'useAI': False})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['topic'], 'speech')
            self.assertEqual(response.json()['mode'], 'retrieval')
