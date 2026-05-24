"""
src/outreach/templates.py

Non-template templates for cold outreach. Defines structured guidelines, 
few-shot exemplars, and system prompts to generate highly human, high-converting outreach.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class OutreachExemplar:
    """A high-converting outreach example showing original context and draft."""
    scenario: str
    company_context: str
    candidate_context: str
    subject: str
    body: str


# Few-shot examples to feed into LLM prompts to teach it how to write cold emails.
OUTREACH_EXEMPLARS: List[OutreachExemplar] = [
    OutreachExemplar(
        scenario="Series A developer tools company looking for backend engineer",
        company_context="Recently shipped an open-source gateway. Focus on Rust and performance.",
        candidate_context="Built a high-performance REST API handling 10k req/sec in Rust/Go.",
        subject="re: gateway performance & gateway design",
        body=(
            "Hi team,\n\n"
            "I saw you recently open-sourced your API gateway. I was reading through the repo "
            "and really liked how you handled connection pooling in Rust.\n\n"
            "At my previous role, I built our core API gateway handling 10,000 requests per second. "
            "We had similar latency bottlenecks and solved them using a similar lock-free design. "
            "I'm deeply interested in what you're building next.\n\n"
            "If you're still looking for backend engineers who love low-level performance, "
            "I'd love to chat. I've attached my resume.\n\n"
            "Best,\n[Candidate Name]"
        ),
    ),
    OutreachExemplar(
        scenario="Enterprise SaaS hiring for Python/Django full-stack developer",
        company_context="Migrating monolith to event-driven microservices. Heavy PostgreSQL usage.",
        candidate_context="5 years Django experience, led migration of billing system to event-driven architecture.",
        subject="microservices migration at [Company Name]",
        body=(
            "Hi [Recruiter Name],\n\n"
            "I noticed your team is currently migrating core workflows to event-driven microservices. "
            "That's a massive undertaking.\n\n"
            "I recently led the migration of a monolithic billing system at my last company to "
            "a Kafka-backed microservice setup, which reduced database load by 40% and resolved "
            "our concurrency issues.\n\n"
            "I know how tricky database-level migrations can get when decoupling. I'd love to "
            "help the team tackle these exact scaling challenges as a full-stack engineer.\n\n"
            "Let me know if you have 10 minutes next week to share what's on the roadmap.\n\n"
            "Thanks,\n[Candidate Name]"
        ),
    ),
]

# Structural rules for different outreach channels.
CHANNEL_RULES: Dict[str, Dict[str, object]] = {
    "email": {
        "max_words": 150,
        "salutation": "Hi [Name]",
        "require_subject": True,
        "style_guidelines": [
            "Never use generic openings like 'Hope this email finds you well'.",
            "Get to the point within 2 sentences.",
            "Must refer to a specific technical artifact (blog, open-source project, or engineering detail).",
            "Call to action must be low-friction (e.g. asking a technical question or offering a short chat).",
        ],
    },
    "linkedin": {
        "max_words": 75,
        "salutation": "Hi [Name]",
        "require_subject": False,
        "style_guidelines": [
            "Keep it extremely punchy — 3-4 sentences max.",
            "No fluff. Immediately establish relevance.",
            "Ask a single direct question about their engineering roadmap.",
        ],
    },
}

# The system instruction prompt guiding recruiter-outreach persona.
OUTREACH_SYSTEM_PROMPT = """
You are a peer-level Software Engineer writing highly personalized outreach.
You NEVER use marketing buzzwords, templates, or canned corporate phrases.
Your writing style is professional yet conversational, concise, and technically precise.
You write as if you are a fellow developer talking to an engineering lead or technical recruiter.

Strict Rules:
1. WORD LIMIT: Under 150 words for emails, under 70 words for LinkedIn.
2. NO CLICHES: Never open with "I hope you are doing well", "I came across your profile", or "I am writing to express my interest".
3. RELEVANCE FIRST: Open immediately with the specific, verified context/connection.
4. ONE SPECIFIC VALUE HOOK: Mention exactly one quantified technical achievement that relates directly to their challenges.
5. NO SALES PITCH: Do not oversell yourself. Let your specific experience spark interest.
"""
