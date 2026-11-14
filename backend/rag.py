from datetime import datetime, timezone
import re
from threading import Lock

from .llm import generate
from .retrieval import tokens

FOREIGN = re.compile(r"\b(usa|u\.s\.a?\.?|united states|united kingdom|uk|canada|australia|california|new york|pakistan|germany|london|singapore|dubai)\b", re.I)
UNSUPPORTED = re.compile(r"\b(fake|forge|bribe|destroy evidence|hide evidence|evade police|win my case|predict|guarantee (?:me|that i|my)|invent|ignore previous|system prompt|jail term|limitation period|filing deadline|divorce|inheritance|bail|tenancy|eviction|income tax|tax return|gst|employment contract|salary dispute)\b", re.I)
FOLLOW_UP = re.compile(r"^(what documents (do i need|should i keep)|what should i (keep|prepare)|what next|how (do|can) i (apply|track|contact|report)( it| this| them)?|where (do|can) i apply|tell me more|what about (the )?fees)[?.! ]*$", re.I)


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
        return {"topic": None, "title": "More evidence is needed", "intro": "The reviewed collection does not provide enough support for that question. I can help with introductory information about consumer complaints, cyber fraud reporting, legal aid, support for women and central RTI requests.",
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
        hits = self.retriever.search(query, limit=8)
        best = hits[0]
        # Similarity is a relevance signal, not a confidence or legal-accuracy percentage.
        relevant = best["lexicalScore"] >= 0.16
        if self.settings.engine == "bge":
            relevant = relevant or best["semanticScore"] >= 0.64
        if not relevant or not tokens(query):
            return self.limited()
        topic_id = best["topic"]
        # Keep a response within one topic to avoid mixing unrelated rules.
        selected = [h for h in hits if h["topic"] == topic_id][:4]
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
