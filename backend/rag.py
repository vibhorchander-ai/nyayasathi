from datetime import datetime, timezone
import re
from threading import Lock

from .llm import generate
from .retrieval import tokens

FOREIGN = re.compile(r"\b(usa|u\.s\.a?\.?|united states|united kingdom|uk|canada|australia|california|new york|pakistan|germany|london|singapore|dubai)\b", re.I)
UNSUPPORTED = re.compile(r"\b(fake|forge|bribe|destroy evidence|hide evidence|evade police|win my case|predict|guarantee (?:me|that i|my)|invent|ignore previous|system prompt|jail term|limitation period|filing deadline|divorce|inheritance|bail|tenancy|eviction|income tax|tax return|gst|employment contract|salary dispute)\b", re.I)
FOLLOW_UP = re.compile(r"^(what documents (do i need|should i keep)|what should i (keep|prepare)|what next|how (do|can) i (apply|track|contact|report)( it| this| them)?|where (do|can) i apply|tell me more|what about (the )?fees)[?.! ]*$", re.I)
ARTICLE = re.compile(r"\b(?:article|art\.?)\s*(\d+[a-z]?(?:\s*\([a-z0-9]+\))*)", re.I)
# These words alone cannot establish coverage. TF-IDF normalises away unseen
# words, so "right to [unknown concept]" used to look like a strong RTI match.
GENERIC = set("right rights freedom fundamental legal law laws article constitution constitutional india indian person persons people citizen citizens state government explain say mean means rules rule there only".split())


def relevant_hit(query, hit, engine):
    specific = set(tokens(query)) - GENERIC
    overlap = specific.intersection(tokens(hit["searchText"]))
    lexical = hit["lexicalScore"] >= 0.16 and bool(overlap)
    # Longer paraphrases can be supported semantically without exact vocabulary.
    # Very short queries need meaningful overlap or a stronger semantic match.
    semantic = engine == "bge" and hit["semanticScore"] >= 0.64 and (
        bool(overlap) or len(specific) >= 3 or hit["semanticScore"] >= 0.78)
    return bool(specific) and (lexical or semantic)


def redact(text):
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email removed]", text)
    text = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[ID removed]", text)
    return re.sub(r"(?:\+91[ -]?)?\b[6-9]\d{9}\b", "[phone removed]", text)


class Pipeline:
    def __init__(self, retriever, settings):
        self.retriever = retriever
        self.settings = settings
        self.catalog = retriever.catalog
        self.topics = {t["id"]: t for t in self.catalog["topics"]}
        self.ai_day = datetime.now(timezone.utc).date()
        self.ai_count = 0
        self.budget_lock = Lock()

    def reserve_ai_call(self):
        with self.budget_lock:
            today = datetime.now(timezone.utc).date()
            if today != self.ai_day:
                self.ai_day, self.ai_count = today, 0
            if self.ai_count >= self.settings.daily_ai_limit:
                return False
            self.ai_count += 1
            return True

    def response(self, topic_id, hits=None, note="", mode="retrieval"):
        topic = self.topics[topic_id]
        hits = hits or []
        points = [{"id": h["id"], "text": h["text"], "source": h["source"],
                   "evidence": [{"chunkId": h["id"], "source": h["source"], "quote": h["text"]}]} for h in hits]
        if topic_id == "emergency":
            points = topic["facts"]
            mode = "guide"
        ids = list(dict.fromkeys([p["source"] for p in points] + topic.get("extraSources", [])))
        return {"topic": topic_id, "title": topic["title"], "intro": topic["intro"],
                "points": points, "steps": topic["steps"],
                "sources": [self.catalog["sources"][i] for i in ids], "caveat": topic["caveat"],
                "link": topic["link"], "followUps": topic["followUps"], "mode": mode, "note": note,
                "reviewedOn": self.catalog["reviewedOn"], "disclaimer": self.catalog["disclaimer"],
                "retrieval": {"engine": self.settings.engine, "model": self.retriever.signature["model"],
                              "corpusHash": self.retriever.corpus_hash, "chunks": hits}}

    def limited(self, note=""):
        scope = ", ".join(t["name"] for t in self.topics.values() if t["id"] != "emergency")
        return {"topic": None, "title": "More evidence is needed", "intro": f"The reviewed collection does not provide enough support for that question. Introductory topics include: {scope}. Please name one topic or use a suggested question.",
                "points": [], "steps": ["Describe one issue without personal identifiers.", "For advice on your specific situation, contact a Legal Services Authority."],
                "sources": [self.catalog["sources"]["aidAccess"]], "caveat": "Coverage is limited to reviewed introductory information for India. No case predictions or state-specific legal determinations.",
                "link": {"label": "Explore free legal aid", "url": self.catalog["sources"]["aid"]["url"]},
                "followUps": ["Can I get free legal aid?", "How do I report an online scam?"],
                "mode": "limited", "note": note, "reviewedOn": self.catalog["reviewedOn"],
                "disclaimer": self.catalog["disclaimer"],
                "retrieval": {"engine": self.settings.engine, "model": self.retriever.signature["model"], "chunks": []}}

    def retrieve(self, question, previous_topic=None):
        # Foreign questions cannot inherit an Indian jurisdiction from the previous turn.
        if FOREIGN.search(question):
            return self.limited("This collection covers India only.")
        normalized = re.sub(r"[^a-z0-9 ]", " ", question.lower())
        if any(f" {word} " in f" {normalized} " for word in self.topics["emergency"]["keywords"]):
            return self.response("emergency")
        if UNSUPPORTED.search(question):
            return self.limited()
        query = question
        if previous_topic in self.topics and FOLLOW_UP.fullmatch(question.strip()):
            query = self.topics[previous_topic]["name"] + ": " + question
        articles = {re.sub(r"\s", "", a.lower()) for a in ARTICLE.findall(query)}
        article_topics = {a: t["id"] for t in self.topics.values() for a in t.get("articles", [])}
        if articles and (not articles.issubset(article_topics) or len({article_topics[a] for a in articles}) != 1):
            return self.limited("The requested articles are not covered together by these introductory notes.")
        # This corpus is small. Search all chunks so required qualifications cannot
        # disappear below an arbitrary top-eight cutoff.
        hits = self.retriever.search(query, limit=len(self.retriever.chunks))
        if articles:
            hits = [h for h in hits if h["topic"] == article_topics[next(iter(articles))]]
        if not hits or (not articles and not relevant_hit(query, hits[0], self.settings.engine)):
            return self.limited()
        topic_id = hits[0]["topic"]
        # Keep a response within one topic to avoid mixing unrelated rules.
        topic_hits = [h for h in hits if h["topic"] == topic_id]
        required = self.topics[topic_id].get("requiredFacts", [])
        selected = sorted(topic_hits, key=lambda h: required.index(h["factId"]) if h["factId"] in required else len(required))[:4]
        result = self.response(topic_id, selected)
        if topic_id == "consumer" and re.search(r"\b(track|status)\b", query, re.I):
            result["title"] = "Track your consumer grievance"
        return result

    async def answer(self, request, client):
        safe_question = redact(request.question)
        result = self.retrieve(safe_question, request.previousTopic)
        return await self.finish(request, safe_question, result, client)

    async def finish(self, request, safe_question, result, client):
        if result["mode"] in {"limited", "guide"}:
            return result
        if not request.useAI:
            result["note"] = "Retrieved reviewed notes. AI generation is off."
            return result
        if not self.settings.groq_key:
            result["note"] = "No LLM key is configured. Showing retrieved notes."
            return result
        if not self.reserve_ai_call():
            result["note"] = "The demo's daily AI limit has been reached. Showing retrieved notes."
            return result
        try:
            points = await generate(client, self.settings, safe_question, result["retrieval"]["chunks"])
            if points is None:
                return self.limited("The retrieved notes do not adequately answer this question.")
            result["points"] = points
            result["mode"] = "rag"
            result["note"] = "AI explanation grounded in retrieved notes. Check the evidence; generated explanations can still be wrong."
        except Exception:
            # Do not expose provider bodies, prompts or credentials in logs/responses.
            result["note"] = "AI is unavailable or its citations could not be validated. Showing retrieved notes."
        return result
