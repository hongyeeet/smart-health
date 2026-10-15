"""Embedding size 768 for knowledge_chunks (D-048: gemini-embedding-001 at 768 dimensions).

0002 created knowledge_chunks.embedding at 1024, a placeholder. memory_episodes (0011) is already 768. The two must
match. pgvector's HNSW index handles at most 2,000 dimensions for the plain vector type, so Gemini's default of
3,072 could not be indexed; 768 can. This only runs while the table is empty: vectors from different sizes or
models cannot be compared, so a non-empty table must be re-embedded, not altered in place.

Revision ID: 0016
Revises: 0015
"""
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    n = conn.exec_driver_sql("SELECT count(*) FROM knowledge_chunks").scalar()
    if n:
        raise RuntimeError(f"knowledge_chunks has {n} rows: re-embed them with the new model instead of altering the column")
    conn.exec_driver_sql("DROP INDEX IF EXISTS knowledge_chunks_embedding_hnsw")
    conn.exec_driver_sql("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE extensions.vector(768)")
    conn.exec_driver_sql("CREATE INDEX knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding extensions.vector_cosine_ops)")


def downgrade():
    conn = op.get_bind()
    n = conn.exec_driver_sql("SELECT count(*) FROM knowledge_chunks").scalar()
    if n:
        raise RuntimeError("knowledge_chunks has rows: do not downgrade the embedding size")
    conn.exec_driver_sql("DROP INDEX IF EXISTS knowledge_chunks_embedding_hnsw")
    conn.exec_driver_sql("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE extensions.vector(1024)")
    conn.exec_driver_sql("CREATE INDEX knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding extensions.vector_cosine_ops)")
