"""${message}

Revision ID: ${up_revision}
Down Revision: ${down_revision}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa


# baseline migrations are applied as raw SQL in database/migrations/;
# this file exists only to satisfy alembic's script directory layout.
down_revision = ${down_revision!r}
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
