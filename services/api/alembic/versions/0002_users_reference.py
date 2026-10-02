"""users and the 11 Reference tables (seeded lookups, loaded in E1-4).

Source: docs/specs/schema.md sections 2, 3, 4, 6, 8 and 9b. Order follows data-flow.md section 6:
Reference tables first, because Silver points at them.

Revision ID: 0002
Revises: 0001
"""
import os

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLES = [  # creation order; dropped in reverse
    "users", "data_sources", "knowledge_documents", "knowledge_chunks", "drug_reference", "drug_aliases",
    "drug_side_effects", "interaction_rules", "foods", "preventive_items", "routing_rules", "population_priors",
]
UPDATED_AT = ["users"]


def run(statements):
    conn = op.get_bind()
    for s in statements:
        conn.exec_driver_sql(s)


def upgrade():
    dim = int(os.environ.get("EMBED_DIM", "1024"))
    run([
        # --- identity (schema.md section 2) ---
        """CREATE TABLE users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email extensions.citext UNIQUE,
            password_hash text,
            locale locale_code NOT NULL DEFAULT 'en',
            timezone text NOT NULL DEFAULT 'Asia/Singapore',
            onboarding_completed_at timestamptz,
            is_demo boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        # --- Reference: data sources and knowledge (sections 8 and 9b) ---
        """CREATE TABLE data_sources (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name text NOT NULL,
            kind text CHECK (kind IN ('dataset','guideline','own')),
            licence text NOT NULL,
            url text,
            retrieved_on date,
            used_for text,
            notes text
        )""",
        """CREATE TABLE knowledge_documents (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            kind knowledge_kind,
            title text,
            source_org text NOT NULL,
            source_url text,
            licence text NOT NULL,
            locale locale_code,
            version text,
            retrieved_on date,
            active boolean DEFAULT true
        )""",
        f"""CREATE TABLE knowledge_chunks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id uuid REFERENCES knowledge_documents(id) ON DELETE CASCADE,
            seq integer,
            content text NOT NULL,
            locale locale_code,
            embedding extensions.vector({dim}) NOT NULL,
            tokens integer,
            UNIQUE (document_id, seq)
        )""",
        "CREATE INDEX knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding extensions.vector_cosine_ops)",
        # --- Reference: drugs (section 3 and 9b) ---
        """CREATE TABLE drug_reference (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            generic_name text NOT NULL UNIQUE,
            brand_names text[] NOT NULL DEFAULT '{}',
            atc_code text,
            kind med_kind NOT NULL,
            knowledge_doc_id uuid REFERENCES knowledge_documents(id)
        )""",
        """CREATE TABLE drug_aliases (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            drug_reference_id uuid NOT NULL REFERENCES drug_reference(id) ON DELETE CASCADE,
            alias text NOT NULL,
            locale locale_code,
            kind text CHECK (kind IN ('brand','generic','local_name')),
            source text NOT NULL
        )""",
        "CREATE UNIQUE INDEX drug_aliases_ref_alias_uq ON drug_aliases (drug_reference_id, lower(alias))",
        "CREATE INDEX drug_aliases_alias_trgm ON drug_aliases USING gin (alias extensions.gin_trgm_ops)",
        """CREATE TABLE drug_side_effects (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            drug_reference_id uuid NOT NULL REFERENCES drug_reference(id) ON DELETE CASCADE,
            effect_key text NOT NULL,
            source text NOT NULL,
            frequency_band text CHECK (frequency_band IN ('very_common','common','uncommon','rare')),
            UNIQUE (drug_reference_id, effect_key)
        )""",
        """CREATE TABLE interaction_rules (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            drug_a_id uuid NOT NULL REFERENCES drug_reference(id),
            drug_b_id uuid NOT NULL REFERENCES drug_reference(id),
            severity interaction_severity NOT NULL,
            mechanism text,
            patient_text_key text NOT NULL,
            source text NOT NULL,
            source_url text,
            CHECK (drug_a_id < drug_b_id),
            UNIQUE (drug_a_id, drug_b_id)
        )""",
        # --- Reference: foods (section 4) ---
        """CREATE TABLE foods (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name text NOT NULL,
            category text,
            gi_source text,
            aliases text[] DEFAULT '{}',
            locale_names jsonb,
            serving_desc text,
            serving_g numeric,
            kcal numeric,
            carbs_g numeric,
            sugar_g numeric,
            fibre_g numeric,
            protein_g numeric,
            fat_g numeric,
            sodium_mg numeric,
            gi gi_category DEFAULT 'unknown',
            flags text[],
            source text NOT NULL
        )""",
        "CREATE INDEX foods_name_trgm ON foods USING gin (name extensions.gin_trgm_ops)",
        # trigram indexes do not work on arrays: aliases get a plain GIN array index (documented deviation)
        "CREATE INDEX foods_aliases_gin ON foods USING gin (aliases)",
        # --- Reference: preventive care, routing, priors (sections 6 and 9b) ---
        """CREATE TABLE preventive_items (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            kind appointment_kind NOT NULL UNIQUE,
            interval_months smallint NOT NULL,
            label_key text NOT NULL,
            source text NOT NULL
        )""",
        """CREATE TABLE routing_rules (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            complication_key text NOT NULL UNIQUE,
            specialty_key text NOT NULL,
            patient_text_key text NOT NULL,
            source text NOT NULL
        )""",
        """CREATE TABLE population_priors (
            metric text NOT NULL,
            sex sex_type NOT NULL,
            age_band text NOT NULL,
            has_diabetes boolean NOT NULL,
            p10 numeric, p25 numeric, p50 numeric, p75 numeric, p90 numeric,
            n integer NOT NULL,
            source text NOT NULL,
            PRIMARY KEY (metric, sex, age_band, has_diabetes, source)
        )""",
    ])
    run([f"CREATE TRIGGER trg_updated_at BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION set_updated_at()" for t in UPDATED_AT])


def downgrade():
    run([f"DROP TABLE IF EXISTS {t} CASCADE" for t in reversed(TABLES)])
