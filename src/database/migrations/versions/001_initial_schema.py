"""
src/database/migrations/versions/001_initial_schema.py
Initial database schema — all tables, indexes, pgvector extension.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── companies ─────────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("domain", sa.String, unique=True),
        sa.Column("linkedin_url", sa.String),
        sa.Column("hq_location", sa.String),
        sa.Column("stage", sa.String),
        sa.Column("headcount", sa.Integer),
        sa.Column("tech_stack", sa.ARRAY(sa.String)),
        sa.Column("engineering_culture", JSONB),
        sa.Column("hiring_urgency", sa.SmallInteger),
        sa.Column("enriched_at", sa.DateTime(timezone=True)),
        sa.Column("raw_metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_companies_domain", "companies", ["domain"])

    # ── jobs ──────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("source_id", sa.String),
        sa.Column("source_url", sa.String),
        sa.Column("location", sa.String),
        sa.Column("remote_type", sa.String),
        sa.Column("employment_type", sa.String),
        sa.Column("seniority", sa.String),
        sa.Column("description", sa.Text),
        sa.Column("requirements", sa.ARRAY(sa.String)),
        sa.Column("tech_stack", sa.ARRAY(sa.String)),
        sa.Column("salary_min", sa.Integer),
        sa.Column("salary_max", sa.Integer),
        sa.Column("salary_currency", sa.String, server_default="USD"),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("enriched", sa.Boolean, server_default="false"),
        sa.Column("opportunity_score", sa.Float),
        sa.Column("fingerprint", sa.String, unique=True),
        sa.Column("raw_metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_index("ix_jobs_seniority", "jobs", ["seniority"])
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])
    op.create_index("ix_jobs_opportunity_score", "jobs", ["opportunity_score"])

    # ── candidates ────────────────────────────────────────────────────────────
    op.create_table(
        "candidates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("phone", sa.String),
        sa.Column("location", sa.String),
        sa.Column("linkedin_url", sa.String),
        sa.Column("github_url", sa.String),
        sa.Column("portfolio_url", sa.String),
        sa.Column("resume_raw", sa.Text),
        sa.Column("resume_structured", JSONB),
        sa.Column("identity_profile", JSONB),
        sa.Column("skills", sa.ARRAY(sa.String)),
        sa.Column("years_experience", sa.Float),
        sa.Column("target_roles", sa.ARRAY(sa.String)),
        sa.Column("target_companies", sa.ARRAY(sa.String)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_candidates_email", "candidates", ["email"])

    # ── applications ──────────────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("candidate_id", UUID(as_uuid=True), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("status", sa.String, server_default="discovered"),
        sa.Column("tailored_resume", sa.Text),
        sa.Column("resume_version", sa.Integer, server_default="1"),
        sa.Column("ats_score", sa.Float),
        sa.Column("authenticity_score", sa.Float),
        sa.Column("recruiter_score", sa.Float),
        sa.Column("interview_probability", sa.Float),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("last_activity", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
        sa.Column("metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_applications_candidate_id", "applications", ["candidate_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    # ── outreach ──────────────────────────────────────────────────────────────
    op.create_table(
        "outreach",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("application_id", UUID(as_uuid=True), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("candidate_id", UUID(as_uuid=True), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("recipient_name", sa.String),
        sa.Column("recipient_email", sa.String),
        sa.Column("recipient_role", sa.String),
        sa.Column("channel", sa.String, server_default="email"),
        sa.Column("subject", sa.String),
        sa.Column("body", sa.Text),
        sa.Column("personalization_signals", JSONB),
        sa.Column("status", sa.String, server_default="drafted"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("replied_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── embeddings (pgvector) ─────────────────────────────────────────────────
    op.create_table(
        "embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("entity_type", sa.String, nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("embedding_model", sa.String, nullable=False),
        sa.Column("vector", Vector(768)),
        sa.Column("chunk_text", sa.Text),
        sa.Column("chunk_index", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_embeddings_entity", "embeddings", ["entity_type", "entity_id"])
    # IVFFlat index for fast approximate nearest-neighbour search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_vector "
        "ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)"
    )

    # ── raw_payloads ──────────────────────────────────────────────────────────
    op.create_table(
        "raw_payloads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("source_id", sa.String),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("processed", sa.Boolean, server_default="false"),
        sa.Column("error", sa.Text),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_raw_payloads_processed", "raw_payloads", ["processed"])


def downgrade() -> None:
    op.drop_table("raw_payloads")
    op.drop_table("embeddings")
    op.drop_table("outreach")
    op.drop_table("applications")
    op.drop_table("candidates")
    op.drop_table("jobs")
    op.drop_table("companies")
    op.execute("DROP EXTENSION IF EXISTS vector")