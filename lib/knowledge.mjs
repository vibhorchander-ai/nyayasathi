// Shared reviewed paraphrases used by the web fallback and Python RAG corpus.
import catalog from '../data/knowledge.json' with { type: 'json' };
export const { topics, sources, reviewedOn, disclaimer } = catalog;
export const coverage = topics.filter(t => t.id !== 'emergency').length;
export const scope = topics.filter(t => t.id !== 'emergency').map(t => t.name).join(', ');
