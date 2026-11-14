export function handleAPI(request: Request, env?: { GROQ_API_KEY?: string; GROQ_MODEL?: string }, fetcher?: typeof fetch): Promise<Response>;
