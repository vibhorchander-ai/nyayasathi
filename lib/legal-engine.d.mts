export function handleAPI(request: Request, env?: { NYAYA_BACKEND_URL?: string; NYAYA_BACKEND_TOKEN?: string; GROQ_API_KEY?: string; GROQ_MODEL?: string }, fetcher?: typeof fetch): Promise<Response>;
