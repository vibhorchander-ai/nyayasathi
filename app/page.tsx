"use client";
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import Link from 'next/link';
import { ArrowDownToLine, ArrowRight, ArrowUp, BookOpen, Check, ChevronRight, CircleHelp, ExternalLink, FileText, HandHeart, Heart, Leaf, LoaderCircle, LockKeyhole, Menu, MessageCircle, Phone, Plus, Scale, Search, ShieldCheck, ShoppingBag, Sparkles, Volume2, X } from 'lucide-react';
import { topics, sources, disclaimer, coverage, reviewedOn } from '../lib/knowledge.mjs';

type Source = { id: string; title: string; publisher: string; url: string; reviewedOn: string };
type EvidenceChunk = { id: string; text: string; source: string; reviewedOn: string };
const modeLabel = (mode: string) => ({ rag: 'AI explanation + evidence', retrieval: 'Retrieved source notes', limited: 'Coverage limit', ai: 'AI-assisted selection', guide: 'Source guide' }[mode] || 'Source guide');
type Answer = { backendAvailable?: boolean; retrieval?: { engine: string; chunks: EvidenceChunk[] }; topic: string | null; title: string; intro: string; points: { id: string; text: string; source: string }[]; steps: string[]; sources: Source[]; caveat: string; link: { label: string; url: string }; followUps: string[]; mode: string; note: string; reviewedOn: string; disclaimer: string };
type Turn = { question: string; answer?: Answer; error?: string };
const icons: Record<string, typeof ShoppingBag> = { bag: ShoppingBag, shield: ShieldCheck, hands: HandHeart, heart: Heart, file: FileText, phone: Phone, speech: MessageCircle, scale: Scale, book: BookOpen };
const subscribeToCapabilities = () => () => {};
const speechAvailable = () => typeof window !== 'undefined' && 'speechSynthesis' in window;
const serverSpeechAvailable = () => false;

export default function Home() {
  const [view, setView] = useState<'chat' | 'sources' | 'help'>('chat');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [aiAvailable, setAiAvailable] = useState(false);
  const [backendAvailable, setBackendAvailable] = useState(false);
  const [useAI, setUseAI] = useState(false);
  const [menu, setMenu] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const [sourceSearch, setSourceSearch] = useState('');
  const [speaking, setSpeaking] = useState(false);
  const canSpeak = useSyncExternalStore(subscribeToCapabilities, speechAvailable, serverSpeechAvailable);
  const [exported, setExported] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const busyRef = useRef(false);
  useEffect(() => {
    fetch('/api/status').then(async r => r.ok ? await r.json() as { aiAvailable?: boolean; backendAvailable?: boolean } : null).then(d => { setAiAvailable(d?.aiAvailable === true); setBackendAvailable(d?.backendAvailable === true); }).catch(() => {});
    return () => { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); };
  }, []);
  useEffect(() => { if (turns.length) bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [turns, busy]);
  useEffect(() => { const close = (event: KeyboardEvent) => { if (event.key === 'Escape') { setPrivacy(false); setMenu(false); } }; window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close); }, []);
  const navigate = (next: 'chat' | 'sources' | 'help') => { setView(next); setMenu(false); };
  const reset = () => { if (busyRef.current) return; setTurns([]); setQuestion(''); navigate('chat'); if (canSpeak) window.speechSynthesis.cancel(); setSpeaking(false); input.current?.focus(); };
  async function ask(value: string) {
    const text = value.trim(); if (!text || text.length > 1200 || busyRef.current) return;
    busyRef.current = true; setBusy(true); setQuestion(''); navigate('chat');
    const previousTopic = turns.at(-1)?.answer?.topic || null;
    setTurns(current => [...current, { question: text }]);
    try {
      const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: text, previousTopic, useAI }), signal: AbortSignal.timeout(22000) });
      const result = await response.json() as Answer & { error?: string }; if (!response.ok) throw new Error(result.error || 'Unable to get a response. Please try again.');
      if (typeof result.backendAvailable === 'boolean') { setBackendAvailable(result.backendAvailable); if (!result.backendAvailable) setAiAvailable(false); }
      setTurns(current => current.map((turn, index) => index === current.length - 1 ? { ...turn, answer: result } : turn));
    } catch (error) {
      const message = error instanceof Error && error.name !== 'TimeoutError' ? error.message : 'The request timed out. Please try again.';
      setTurns(current => current.map((turn, index) => index === current.length - 1 ? { ...turn, error: message } : turn));
    } finally { busyRef.current = false; setBusy(false); input.current?.focus(); }
  }
  function download() {
    const content = ['NyayaSathi · Conversation notes', new Date().toLocaleDateString('en-IN'), disclaimer, '', ...turns.flatMap(t => ['YOU: ' + t.question, ...(t.answer ? [t.answer.title, t.answer.intro, ...t.answer.points.map(p => '- ' + p.text), 'PRACTICAL NEXT STEPS', ...t.answer.steps.map((s, i) => `${i + 1}. ${s}`), t.answer.caveat, 'SOURCES (reviewed ' + t.answer.reviewedOn + ')', ...t.answer.sources.map(s => s.title + '\n' + s.url), 'RETRIEVED NOTES (reviewed paraphrases)', ...(t.answer.retrieval?.chunks || []).map(c => c.text + '\nSource: ' + (t.answer!.sources.find(s => s.id === c.source)?.url || '')), 'Mode: ' + modeLabel(t.answer.mode)] : [t.error || 'No response']), ''])].join('\n');
    const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'nyayasathi-notes.txt'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    setExported(true); setTimeout(() => setExported(false), 2000);
  }
  function speak(answer: Answer) {
    window.speechSynthesis.cancel(); if (speaking) { setSpeaking(false); return; }
    const speech = new SpeechSynthesisUtterance([answer.title, answer.intro, ...answer.points.map(p => p.text), 'Next steps.', ...answer.steps, answer.caveat, disclaimer].join(' '));
    speech.lang = 'en-IN'; speech.rate = 0.94; speech.onend = () => setSpeaking(false); speech.onerror = () => setSpeaking(false); setSpeaking(true); window.speechSynthesis.speak(speech);
  }
  const filteredSources = Object.values(sources).filter(s => (s.title + s.publisher).toLowerCase().includes(sourceSearch.toLowerCase()));
  return <div className="app-shell">
    {menu && <button className="nav-backdrop" aria-label="Close navigation" onClick={() => setMenu(false)} />}
    <aside className={'sidebar ' + (menu ? 'sidebar-open' : '')}>
      <Link href="/" className="brand" aria-label="NyayaSathi home"><span className="brand-symbol"><Scale size={25} strokeWidth={1.6} /></span><span>Nyaya<span className="brand-light">Sathi</span><small>YOUR RIGHTS, WITH CLARITY</small></span></Link>
      <button className="new-chat" onClick={reset} disabled={busy}><Plus size={17} /> New conversation</button><span className="nav-label">YOUR GUIDE</span>
      <nav aria-label="Main navigation"><button className={view === 'chat' ? 'active' : ''} onClick={() => navigate('chat')}><MessageCircle size={18} /> Ask a question <ChevronRight size={15} /></button><button className={view === 'sources' ? 'active' : ''} onClick={() => navigate('sources')}><BookOpen size={18} /> Source library</button><button className={view === 'help' ? 'active' : ''} onClick={() => navigate('help')}><HandHeart size={18} /> Find legal help</button></nav>
      <div className="sidebar-note"><span className="little-line" /><p>A little understanding.<br />A more confident next step.</p><span>Built for access to justice.</span></div>
      <div className="sidebar-bottom"><div className="india-mark"><i /><i /><i /></div><span>Made for people in India</span><button onClick={() => setPrivacy(true)}><LockKeyhole size={13} /> About your privacy</button></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="topbar-left"><button className="mobile-menu icon-button" onClick={() => setMenu(true)} aria-label="Open navigation"><Menu size={22} /></button><span className="breadcrumb">Your legal companion</span><span className="header-divider" /><span className="jurisdiction">India <span>·</span> English</span></div><div className="status-pill"><span className="status-dot" />{aiAvailable && useAI ? 'AI explanation + sources' : backendAvailable ? 'Source retrieval' : 'Source guide'}</div></header>
      <div className="content-layout"><main id="main-content" className={view === 'chat' ? 'main-pane' : 'main-pane secondary-pane'}>
        {view === 'chat' && <>
          {turns.length === 0 ? <section className="welcome"><div className="eyebrow"><span /> A LITTLE CLARITY GOES A LONG WAY</div><h1>Know your rights.<br /><em>Find your next step.</em></h1><p className="intro">Legal questions can feel complicated. Let’s make them simpler,<br className="desktop-break" /> with plain-English guidance and sources you can check.</p><div className="trust-row"><span><BookOpen size={15} /> Official sources</span><span><Leaf size={15} /> Free to use</span><span><LockKeyhole size={14} /> No chat history saved</span></div><div className="section-heading"><h2>What’s on your mind?</h2><span>Choose a starting point</span></div><div className="topic-grid">{topics.map(topic => { const Icon = icons[topic.icon]; return <button className={'topic-card topic-' + topic.id} key={topic.id} onClick={() => ask(topic.example)} disabled={busy}><span className="topic-icon"><Icon size={21} strokeWidth={1.6} /></span><span><strong>{topic.name}</strong><small>{topic.short}</small></span><ArrowRight className="topic-arrow" size={16} /></button>; })}</div><p className="starter-note"><Sparkles size={14} /> Start with a topic, or tell me what happened in your own words.</p></section> : <section className="conversation" aria-label="Conversation">
            <div className="conversation-toolbar"><span><MessageCircle size={15} /> Your conversation</span><button onClick={download} disabled={busy}><ArrowDownToLine size={15} />{exported ? 'Downloaded' : 'Save notes'}</button></div>
            {turns.map((turn, index) => <div className="turn" key={index}><div className="user-message"><span className="you-label">YOU</span><p>{turn.question}</p></div>
              {turn.answer && <article className="answer"><div className="answer-brand"><span className="mini-logo"><Scale size={17} /></span><strong>NyayaSathi</strong><span className={'answer-mode ' + (turn.answer.mode === 'limited' ? 'limited' : '')}>{modeLabel(turn.answer.mode)}</span></div>
                {turn.answer.note && <p className="notice">{turn.answer.note}</p>}<h2>{turn.answer.title}</h2><p>{turn.answer.intro}</p>
                {turn.answer.points.length > 0 && <div className="fact-list">{turn.answer.points.map(point => <div className="fact" key={point.id}><Check size={16} /><p>{point.text} <a className="citation" href={turn.answer!.sources.find(s => s.id === point.source)?.url} target="_blank" rel="noopener noreferrer" aria-label={'Read source for: ' + point.text.slice(0, 50)}>[{turn.answer!.sources.findIndex(s => s.id === point.source) + 1}]</a></p></div>)}</div>}
                <div className="next-steps"><h3>Practical next steps</h3><ol>{turn.answer.steps.map((step, i) => <li key={i}><span>{i + 1}</span>{step}</li>)}</ol></div><a className="official-link" href={turn.answer.link.url} target={turn.answer.link.url.startsWith('tel:') ? undefined : '_blank'} rel="noopener noreferrer">{turn.answer.link.label}<ExternalLink size={14} /></a><p className="answer-caveat"><CircleHelp size={15} />{turn.answer.caveat}</p>
                <details className="source-details"><summary><BookOpen size={15} /> {turn.answer.sources.length} official source{turn.answer.sources.length !== 1 ? 's' : ''}<span>Reviewed {turn.answer.reviewedOn}</span></summary><div>{turn.answer.sources.map((source, i) => <a key={source.id} href={source.url} target="_blank" rel="noopener noreferrer"><span>[{i + 1}] {source.title}<small>{source.publisher}</small></span><ExternalLink size={14} /></a>)}</div></details>
                {Boolean(turn.answer.retrieval?.chunks.length) && <details className="retrieved-evidence"><summary><BookOpen size={15} /> Read the retrieved evidence</summary><p>Reviewed summaries of official information, not quotations from legislation. AI explanations can still make mistakes.</p>{turn.answer.retrieval!.chunks.map(chunk => <blockquote key={chunk.id}><p>{chunk.text}</p><footer><a href={turn.answer!.sources.find(source => source.id === chunk.source)?.url} target="_blank" rel="noopener noreferrer">Check official source <ExternalLink size={12} /></a><span>Reviewed {chunk.reviewedOn}</span></footer></blockquote>)}</details>}
                <div className="answer-footer"><span>{turn.answer.mode === 'rag' ? 'AI explanation with validated evidence references. Check the sources.' : 'Based on a limited, reviewed source collection.'}</span>{canSpeak && <button onClick={() => speak(turn.answer!)}><Volume2 size={15} />{speaking ? 'Stop reading' : 'Read aloud'}</button>}</div>
                {index === turns.length - 1 && <div className="follow-ups">{turn.answer.followUps.map(text => <button key={text} onClick={() => ask(text)} disabled={busy}>{text}<ArrowRight size={13} /></button>)}</div>}
              </article>}
              {turn.error && <div className="error-message" role="alert"><p>{turn.error}</p><button onClick={() => ask(turn.question)} disabled={busy}>Try again <ArrowRight size={14} /></button></div>}
            </div>)}{busy && <div className="loading" role="status"><LoaderCircle size={19} className="spin" />{useAI && aiAvailable ? 'Finding relevant guidance in the source collection…' : 'Looking through the source guide…'}</div>}<div ref={bottom} />
          </section>}
          <div className="composer-area"><form className="composer" onSubmit={event => { event.preventDefault(); ask(question); }}><label className="sr-only" htmlFor="question">Describe your legal question</label><textarea ref={input} id="question" rows={2} value={question} maxLength={1200} onChange={e => setQuestion(e.target.value)} placeholder="Tell me what happened, or ask a legal question…" onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); ask(question); } }} /><div className="composer-bottom"><span><LockKeyhole size={12} /> Leave out names, IDs and account details.</span><div><span className="character-count">{question.length > 900 ? `${question.length}/1200` : '↵ to send'}</span><button className="send-button" type="submit" disabled={!question.trim() || busy} aria-label="Send question">{busy ? <LoaderCircle size={18} className="spin" /> : <ArrowUp size={20} />}</button></div></div></form>
            {aiAvailable ? <label className="ai-consent"><input type="checkbox" checked={useAI} onChange={e => setUseAI(e.target.checked)} /> Use AI to explain the retrieved information <span>· Sends the question to Groq. <button type="button" onClick={() => setPrivacy(true)}>Details</button></span></label> : <p className="mode-note">{backendAvailable ? 'Source retrieval is active. Add a free Groq key to enable optional AI explanations.' : 'Built-in source guide is active. Start and connect the Python backend to enable retrieval.'}</p>}<p className="disclaimer">Legal information, not legal advice. For advice on your case, speak with a qualified lawyer.</p>
          </div>
        </>}
        {view === 'sources' && <section className="library"><div className="eyebrow"><span /> CHECK THE INFORMATION</div><h1>Clarity starts<br />with <em>a source.</em></h1><p className="intro">Explore the official information behind this guide. The collection was reviewed on {reviewedOn} and is not updated automatically.</p><div className="library-search"><Search size={18} /><label className="sr-only" htmlFor="source-search">Search sources</label><input id="source-search" value={sourceSearch} onChange={e => setSourceSearch(e.target.value)} placeholder="Find a source or government service…" /></div><div className="source-library">{filteredSources.map(source => <a href={source.url} target="_blank" rel="noopener noreferrer" className="library-card" key={source.id}><span className="library-icon"><BookOpen size={20} /></span><span><strong>{source.title}</strong><small>{source.publisher}</small><span className="source-domain">{new URL(source.url).hostname} · Reviewed {source.reviewedOn}</span></span><ExternalLink size={17} /></a>)}{!filteredSources.length && <p>No sources match that search. Try “speech”, “education”, “legal aid” or “RTI”.</p>}</div><div className="scope-note"><ShieldCheck size={23} /><div><h3>Small scope. Visible evidence.</h3><p>This prototype provides introductory guidance on {coverage} topics, plus emergency signposting. It does not cover every law, state rule or court decision. Source links and review dates help you judge what it can support.</p></div></div></section>}
        {view === 'help' && <section className="help-page"><div className="eyebrow"><span /> THERE IS A HUMAN NEXT STEP</div><h1>You don’t have to<br /><em>figure it out alone.</em></h1><p className="intro">These official services can help you take the next step. NyayaSathi does not make calls or submit complaints on your behalf.</p><div className="help-cards">{[
          { number: '15100', name: 'Free legal aid', label: 'National Legal Services Authority', text: 'Ask about legal assistance, eligibility and your nearest legal services institution.', url: sources.aidAccess.url, color: 'green' },
          { number: '1915', name: 'Consumer grievances', label: 'National Consumer Helpline', text: 'For consumer complaints. Published call hours: 8 AM–8 PM, excluding national holidays.', url: sources.contact.url, color: 'gold' },
          { number: '1930', name: 'Financial cyber fraud', label: 'Cybercrime reporting', text: 'Report suspected financial cyber fraud promptly. You can also visit cybercrime.gov.in.', url: sources.cyber.url, color: 'blue' },
          { number: '112', name: 'Immediate emergency', label: 'Emergency Response Support System', text: 'For immediate danger and emergency assistance. Call when it is safe to do so.', url: sources.emergency.url, color: 'rose' }
        ].map(help => <article className={'help-card ' + help.color} key={help.number}><span>{help.label}</span><h2>{help.name}</h2><p>{help.text}</p><div><a className="phone-number" href={'tel:' + help.number}><Phone size={20} />{help.number}</a><a href={help.url} target="_blank" rel="noopener noreferrer">Official source <ExternalLink size={13} /></a></div></article>)}</div><button className="help-cta" onClick={() => ask('I cannot afford a lawyer. How can I apply for free legal aid?')}><HandHeart size={21} /><span><strong>Not sure where to begin?</strong><small>Learn how to apply for free legal aid.</small></span><ArrowRight size={18} /></button></section>}
      </main><aside className="context-rail"><div className="rail-top"><div className="seal"><Scale size={32} strokeWidth={1.2} /></div><span className="eyebrow-small">INFORMATION YOU CAN CHECK</span><h2>A clearer path<br />starts here.</h2><p>Understand the basics.<br />See the sources.<br />Decide your next step.</p></div><div className="how-it-works"><h3>How this guide helps</h3>{[['01', 'Start with your question', 'Everyday language is welcome.'], ['02', 'Understand your options', 'Read guidance with official sources.'], ['03', 'Find the right support', 'Connect with a relevant service.']].map(item => <div className="how-step" key={item[0]}><span>{item[0]}</span><div><strong>{item[1]}</strong><p>{item[2]}</p></div></div>)}</div><div className="human-help"><HandHeart size={23} strokeWidth={1.5} /><h3>Need to speak to someone?</h3><p>Explore free legal assistance through NALSA.</p><a href="tel:15100"><Phone size={16} /> 15100 <span>Legal aid helpline</span></a><button onClick={() => navigate('help')}>Find more support <ArrowRight size={14} /></button></div><div className="independent-note"><ShieldCheck size={15} /><p>Independent hackathon prototype.<br />Not a government service or law firm.</p></div></aside></div>
    </div>
    {privacy && <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) setPrivacy(false); }}><section className="privacy-modal" role="dialog" aria-modal="true" aria-labelledby="privacy-title"><button autoFocus className="modal-close icon-button" aria-label="Close privacy details" onClick={() => setPrivacy(false)}><X size={22} /></button><LockKeyhole size={29} /><h2 id="privacy-title">Your question, with care.</h2><p>Conversations stay in this page’s memory and disappear when you reload or close it. We do not save chat history to a database or browser storage.</p><p>Questions are sent to this app’s server. The web server forwards questions to the configured Python backend. If you enable AI explanations, a redacted question and the relevant retrieved notes are also sent to Groq. Basic email, phone and ID patterns are removed before AI processing; this does not guarantee anonymisation.</p><p>Hosting and AI providers may process operational data under their own policies. Please leave out names, addresses, passwords, IDs and account information. Downloaded notes include your questions and remain on your device.</p><a href="https://console.groq.com/docs/your-data" target="_blank" rel="noopener noreferrer">Read Groq’s data policy <ExternalLink size={14} /></a><button className="modal-done" onClick={() => setPrivacy(false)}>Got it</button></section></div>}
  </div>;
}
