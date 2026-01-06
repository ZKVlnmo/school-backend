"""remove is_submitted from student_task

Revision ID: 99a6ca5743b0
Revises: b730e23d9986
Create Date: 2026-01-04 00:50:13.421624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99a6ca5743b0'
down_revision: Union[str, None] = 'b730e23d9986'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
