"""remove is_submitted from student_task

Revision ID: b730e23d9986
Revises: 3f887b562b56
Create Date: 2026-01-04 00:47:03.232234

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b730e23d9986'
down_revision: Union[str, None] = '3f887b562b56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
