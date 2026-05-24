"""
src/enrichment/skill_extractor.py

Local skill extraction — runs entirely with regex + curated taxonomy.
Zero LLM cost. Fast. Used for pre-filtering before semantic matching.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ─── Curated skill taxonomy ───────────────────────────────────────────────────
# Organised by domain. Used for normalisation and classification.

SKILL_TAXONOMY: dict[str, list[str]] = {
    "languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
        "rust", "ruby", "scala", "kotlin", "swift", "php", "r", "matlab", "sql",
    ],
    "backend_frameworks": [
        "fastapi", "django", "flask", "express", "express.js", "node.js", "spring boot",
        "rails", "laravel", "gin", "actix", "nestjs", "hapi",
    ],
    "frontend_frameworks": [
        "react", "vue", "angular", "next.js", "svelte", "nuxt", "gatsby",
        "tailwind", "tailwindcss", "redux", "graphql",
    ],
    "databases": [
        "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
        "cassandra", "elasticsearch", "dynamodb", "neo4j", "clickhouse",
        "bigquery", "snowflake", "pinecone", "pgvector",
    ],
    "messaging": [
        "kafka", "rabbitmq", "sqs", "pubsub", "nats", "celery", "sidekiq",
    ],
    "infrastructure": [
        "docker", "kubernetes", "k8s", "terraform", "helm", "ansible",
        "nginx", "aws", "gcp", "azure", "s3", "lambda", "ec2", "cloudfront",
        "ci/cd", "github actions", "jenkins", "gitlab ci",
    ],
    "ml_ai": [
        "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "numpy",
        "pandas", "hugging face", "transformers", "langchain", "langgraph",
        "ollama", "openai", "gemini", "rag", "llm", "nlp", "computer vision",
        "detectron2", "yolo", "sam", "mlflow", "wandb",
    ],
    "ai_agents": [
        "crewai", "autogen", "langchain agents", "langgraph", "tool use",
        "function calling", "prompt engineering", "retrieval augmented generation",
    ],
}

# Flattened lookup: normalised_name → canonical_name
_SKILL_LOOKUP: dict[str, str] = {}
for _domain, _skills in SKILL_TAXONOMY.items():
    for _skill in _skills:
        _SKILL_LOOKUP[_skill.lower()] = _skill


@dataclass
class ExtractedSkills:
    raw: list[str]                          # as they appear in text
    normalised: list[str]                   # canonical names
    by_domain: dict[str, list[str]] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)  # not in taxonomy


class SkillExtractor:
    """
    Fast regex-based skill extractor.
    No LLM calls. Used for ranking, filtering, and deduplication.
    """

    def extract(self, text: str) -> ExtractedSkills:
        text_lower = text.lower()
        found_raw: list[str] = []
        found_normalised: list[str] = []
        by_domain: dict[str, list[str]] = {}

        for domain, skills in SKILL_TAXONOMY.items():
            matched: list[str] = []
            for skill in skills:
                # Word-boundary match, allow punctuation neighbours
                pattern = r"(?<![a-zA-Z])" + re.escape(skill) + r"(?![a-zA-Z])"
                if re.search(pattern, text_lower):
                    found_raw.append(skill)
                    found_normalised.append(_SKILL_LOOKUP.get(skill.lower(), skill))
                    matched.append(skill)
            if matched:
                by_domain[domain] = matched

        # Detect unknown tech-sounding tokens (CamelCase or all-caps 3-10 chars)
        tokens = re.findall(r"\b[A-Z][a-z]+[A-Z]\w*\b|\b[A-Z]{2,10}\b", text)
        known_lower = {s.lower() for s in found_raw}
        unknown = [t for t in tokens if t.lower() not in known_lower and len(t) > 2]

        return ExtractedSkills(
            raw=list(dict.fromkeys(found_raw)),          # dedup, preserve order
            normalised=list(dict.fromkeys(found_normalised)),
            by_domain=by_domain,
            unknown=list(dict.fromkeys(unknown))[:10],
        )

    def overlap_score(self, resume_skills: list[str], jd_skills: list[str]) -> float:
        """
        Jaccard similarity between two skill sets after normalisation.
        Returns 0.0–1.0.
        """
        a = {s.lower() for s in resume_skills}
        b = {s.lower() for s in jd_skills}
        union = a | b
        if not union:
            return 0.0
        return len(a & b) / len(union)

    def classify_domain(self, skills: list[str]) -> str:
        """Classify primary domain based on skill distribution."""
        domain_counts: dict[str, int] = {}
        skills_lower = {s.lower() for s in skills}
        for domain, domain_skills in SKILL_TAXONOMY.items():
            domain_counts[domain] = sum(1 for s in domain_skills if s in skills_lower)

        if not any(domain_counts.values()):
            return "fullstack"

        top = max(domain_counts, key=domain_counts.get)  # type: ignore[arg-type]
        # Remap taxonomy domain names to role types
        mapping = {
            "ml_ai": "ml",
            "backend_frameworks": "backend",
            "frontend_frameworks": "frontend",
            "infrastructure": "devops",
            "ai_agents": "ml",
        }
        return mapping.get(top, top)