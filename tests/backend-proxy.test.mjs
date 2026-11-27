import test from 'node:test';
import assert from 'node:assert/strict';
import { handleAPI, localAnswer } from '../lib/legal-engine.mjs';
import { backendAnswer, backendStatus } from '../lib/backend-proxy.mjs';
import { coverage } from '../lib/knowledge.mjs';
const env = { NYAYA_BACKEND_URL: 'http://127.0.0.1:8000', NYAYA_BACKEND_TOKEN: 'test-token' };
let sequence = 0;
const request = () => new Request('https://demo.example/api/chat', { method: 'POST', headers: { 'content-type': 'application/json', 'cf-connecting-ip': `proxy-${++sequence}` }, body: JSON.stringify({ question: 'How do I get a refund?', useAI: true }) });
test('expanded coverage is preserved through the backend proxy', async () => {
  const status = await backendStatus(env, async () => Response.json({ backendAvailable: true, engine: 'bge', coverage, aiAvailable: false }));
  assert.equal(status.coverage, coverage);
});
test('speech still works when the free Python service is unavailable', async () => {
  const req = new Request('https://demo.example/api/chat', { method: 'POST', headers: { 'content-type': 'application/json', 'cf-connecting-ip': 'speech-outage-test' }, body: JSON.stringify({ question: 'what is a right to speech?', useAI: true }) });
  const result = await (await handleAPI(req, env, async () => { throw new Error('asleep'); })).json();
  assert.equal(result.topic, 'speech');
  assert.equal(result.mode, 'guide');
  assert.equal(result.backendAvailable, false);
  assert.equal(result.points.length, 2);
});
test('same-origin API forwards consent to Python and keeps the token server-side', async () => {
  let sent;
  const result = { ...localAnswer('I need a refund'), mode: 'retrieval' };
  const fetcher = async (url, options) => { assert.equal(url.href, 'http://127.0.0.1:8000/api/chat'); sent = options; return Response.json(result); };
  const response = await handleAPI(request(), env, fetcher);
  assert.equal((await response.json()).mode, 'retrieval');
  assert.equal(JSON.parse(sent.body).useAI, true);
  assert.equal(sent.redirect, 'manual');
  assert.equal(sent.headers.Authorization, 'Bearer test-token');
});
test('Python failure falls back with an explicit source-guide label', async () => {
  for (const fetcher of [async () => { throw new Error('offline'); }, async () => new Response('', { status: 429 }), async () => Response.json({ mode: 'rag', points: [] })]) {
    const body = await (await handleAPI(request(), env, fetcher)).json();
    assert.equal(body.mode, 'guide'); assert.equal(body.backendAvailable, false); assert.match(body.note, /Python backend is unavailable/);
  }
});
test('backend status advertises retrieval and never reveals keys', async () => {
  const response = await handleAPI(new Request('https://demo.example/api/status'), env, async () => Response.json({ backendAvailable: true, aiAvailable: true, engine: 'bge', secret: 'test-token' }));
  const text = await response.text(); assert.ok(!text.includes('test-token')); assert.equal(JSON.parse(text).backendAvailable, true);
});
test('proxy rejects unsafe backend schemes, links and missing citations', async () => {
  await assert.rejects(backendAnswer({}, { NYAYA_BACKEND_URL: 'http://remote.example' }, request(), async () => { throw new Error('must not fetch'); }));
  const answer = { ...localAnswer('refund'), mode: 'rag', sources: [{ id: 'consumer', url: 'https://evil.example' }] };
  await assert.rejects(backendAnswer({}, env, request(), async () => Response.json(answer)));
});
