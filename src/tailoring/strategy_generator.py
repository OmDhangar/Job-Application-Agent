from __future__ import annotations
 
import re
from dataclasses import dataclass, field
from src.schemas.candidate import IdentityProfile
from src.enrichment.jd_analyzer import JDAnalysis
 
 
# ─── Strategy ─────────────────────────────────────────────────────────────────
 
@dataclass
class SectionWeight:
    section: str
    weight: float
    action: str    # expand | compress | reorder | keep
 
 
@dataclass
class StrategyPlan:
    target_role_type: str
    primary_emphasis: list[str]
    secondary_emphasis: list[str]
    compress: list[str]
    section_weights: list[SectionWeight]
    bullet_focus: list[str]
    ats_keywords: list[str]
    authenticity_notes: str
 
 
_ROLE_SIGNALS: dict[str, list[str]] = {
    "backend":  ["api", "database", "microservice", "kafka", "rabbitmq", "redis", "postgres", "grpc", "rest"],
    "ml":       ["model", "training", "inference", "pytorch", "tensorflow", "llm", "rag", "langchain", "hugging"],
    "frontend": ["react", "vue", "angular", "typescript", "css", "ux", "component", "next"],
    "devops":   ["kubernetes", "docker", "ci/cd", "terraform", "helm", "aws", "gcp", "pipeline"],
    "data":     ["spark", "airflow", "dbt", "warehouse", "etl", "sql", "analytics", "tableau"],
    "research": ["paper", "publication", "experiment", "ablation", "arxiv", "ieee", "novel"],
}
 
_BULLET_VERBS: dict[str, list[str]] = {
    "backend":  ["built", "scaled", "optimized", "reduced latency", "designed", "deployed", "architected"],
    "ml":       ["trained", "improved accuracy", "deployed", "fine-tuned", "reduced error", "benchmarked"],
    "frontend": ["implemented", "improved UX", "reduced load time", "built", "redesigned"],
    "devops":   ["automated", "reduced downtime", "migrated", "provisioned", "containerized"],
    "data":     ["modeled", "ingested", "reduced pipeline time", "built", "orchestrated"],
    "research": ["published", "proposed", "demonstrated", "evaluated", "developed"],
}
 
 
class StrategyGenerator:
    def generate(
        self,
        candidate: IdentityProfile,
        jd: JDAnalysis,
        fit_scores: dict[str, float],
    ) -> StrategyPlan:
        role_type = jd.role_type or self._classify(jd.tech_stack + jd.required_skills)
 
        # Rank candidate projects by relevance
        project_scores = {p: fit_scores.get(p, 0.5) for p in candidate.project_titles}
        ranked = sorted(project_scores, key=project_scores.get, reverse=True)  # type: ignore[arg-type]
 
        primary = ranked[:2]
        secondary = ranked[2:4] if len(ranked) > 2 else []
        compress = ranked[-2:] if len(ranked) > 4 else []
 
        # Only include JD keywords the candidate genuinely has
        authentic_kws = [
            kw for kw in jd.ats_keywords
            if any(kw.lower() in s.lower() for s in candidate.core_skills + candidate.project_titles)
        ]
 
        return StrategyPlan(
            target_role_type=role_type,
            primary_emphasis=primary or candidate.project_titles[:2],
            secondary_emphasis=secondary,
            compress=compress,
            section_weights=self._section_weights(role_type),
            bullet_focus=_BULLET_VERBS.get(role_type, ["built", "improved", "led"]),
            ats_keywords=authentic_kws[:12],
            authenticity_notes=(
                f"Preserve candidate voice: {', '.join(candidate.voice_markers[:2])}"
                if candidate.voice_markers else "Maintain original professional tone"
            ),
        )
 
    def _classify(self, signals: list[str]) -> str:
        counts: dict[str, int] = {rt: 0 for rt in _ROLE_SIGNALS}
        for sig in [s.lower() for s in signals]:
            for role_type, kws in _ROLE_SIGNALS.items():
                if any(kw in sig for kw in kws):
                    counts[role_type] += 1
        return max(counts, key=counts.get) if any(counts.values()) else "backend"  # type: ignore[arg-type]
 
    def _section_weights(self, role_type: str) -> list[SectionWeight]:
        base = [
            SectionWeight("experience", 0.9, "expand"),
            SectionWeight("projects",   0.85, "reorder"),
            SectionWeight("skills",     0.7, "reorder"),
            SectionWeight("education",  0.4, "compress"),
        ]
        if role_type == "research":
            base.insert(0, SectionWeight("publications", 1.0, "expand"))
        return base