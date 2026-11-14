import test from 'node:test';
import assert from 'node:assert/strict';
import { handleAPI, localAnswer } from '../lib/legal-engine.mjs';
import { backendAnswer } from '../lib/backend-proxy.mjs';
const env = { NYAYA_BACKEND_URL: 'http://127.0.0.1:8000', NYAYA_BACKEND_TOKEN: 'test-token' };
let sequence = 0;
const request = () => new Request('https://demo.example/api/chat', { method: 'POST', headers: { 'content-type': 'application/json', 'cf-connecting-ip': `proxy-${++sequence}` }, body: JSON.stringify({ question: 'How do I get a refund?', useAI: true }) });
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
