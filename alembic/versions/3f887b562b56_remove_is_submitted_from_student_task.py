"""remove is_submitted from student_task

Revision ID: 3f887b562b56
Revises: 38f2639f5e8f
Create Date: 2026-01-04 00:46:49.377244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f887b562b56'
down_revision: Union[str, None] = '38f2639f5e8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_column('student_task', 'is_submitted')

def downgrade():
    op.add_column('student_task', sa.Column('is_submitted', sa.Boolean(), nullable=False))