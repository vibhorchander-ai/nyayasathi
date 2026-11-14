// Browser requests stay same-origin; backend credentials never enter client bundles.
function backendURL(env, path) {
  const base = new URL(env.NYAYA_BACKEND_URL);
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(base.hostname);
  if (base.username || base.password || (base.protocol !== 'https:' && !(local && base.protocol === 'http:'))) throw new Error('Use HTTPS for a remote backend');
  return new URL(path, base);
}
function headers(env, request) {
  return { 'Content-Type': 'application/json',
    ...(env.NYAYA_BACKEND_TOKEN ? { Authorization: `Bearer ${env.NYAYA_BACKEND_TOKEN}` } : {}),
    ...(request ? { 'X-Nyaya-Client': request.headers.get('cf-connecting-ip') || 'local' } : {}) };
}
export async function backendStatus(env, fetcher = fetch) {
  const response = await fetcher(backendURL(env, '/api/status'), { headers: headers(env), signal: AbortSignal.timeout(3500), redirect: 'manual' });
  if (!response.ok) throw new Error('Backend unavailable');
  const result = await response.json();
  if (result.backendAvailable !== true || !['bge', 'tfidf'].includes(result.engine)) throw new Error('Invalid backend status');
  return { aiAvailable: result.aiAvailable === true, backendAvailable: true, engine: result.engine, reviewedOn: result.reviewedOn, coverage: 5 };
}
export async function backendAnswer(body, env, request, fetcher = fetch) {
  const response = await fetcher(backendURL(env, '/api/chat'), { method: 'POST', headers: headers(env, request), body: JSON.stringify(body), signal: AbortSignal.timeout(18000), redirect: 'manual' });
  if (!response.ok) throw new Error('Backend unavailable');
  const result = await response.json();
  if (!result || !['rag', 'retrieval', 'guide', 'limited'].includes(result.mode) ||
      !Array.isArray(result.points) || !Array.isArray(result.sources) || !Array.isArray(result.steps) ||
      !Array.isArray(result.followUps) || typeof result.title !== 'string' || typeof result.intro !== 'string' ||
      typeof result.caveat !== 'string' || typeof result.link?.url !== 'string' || typeof result.link?.label !== 'string') throw new Error('Invalid backend answer');
  for (const source of result.sources) {
    const url = new URL(source.url);
    if (url.protocol !== 'https:' || !url.hostname.endsWith('.gov.in')) throw new Error('Invalid source');
  }
  for (const point of result.points) if (typeof point.text !== 'string' || !result.sources.some(s => s.id === point.source)) throw new Error('Uncited answer');
  const link = new URL(result.link.url);
  if (!(link.protocol === 'https:' && link.hostname.endsWith('.gov.in')) && result.link.url !== 'tel:112') throw new Error('Invalid assistance link');
  return { ...result, backendAvailable: true };
}
