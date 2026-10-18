"""add unique constraint to sentiment_analyses
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "b3c9f2a1c123"
down_revision = "4cfe636444f4"
branch_labels = None
depends_on = None


def upgrade():
    # Delete duplicate rows, keeping the lowest id per (article_id, company_id, model_used)
    conn = op.get_bind()
    conn.execute(
        text(
            """
            DELETE FROM sentiment_analyses
            WHERE id NOT IN (
                SELECT MIN(id) FROM sentiment_analyses
                GROUP BY article_id, company_id, model_used
            );
            """
        )
    )
    # Add unique constraint (SQLite compatible via batch_alter_table)
    with op.batch_alter_table("sentiment_analyses") as batch_op:
        batch_op.create_unique_constraint(
            "uq_sentiment_article_company_model",
            ["article_id", "company_id", "model_used"],
        )


def downgrade():
    # Remove unique constraint
    with op.batch_alter_table("sentiment_analyses") as batch_op:
        batch_op.drop_constraint("uq_sentiment_article_company_model", type_="unique")
