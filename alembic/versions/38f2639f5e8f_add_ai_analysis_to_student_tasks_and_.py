"""add ai_analysis to student_task and enable_ai_analysis to tasks

Revision ID: 38f2639f5e8f
Revises: d92307c7b838
Create Date: 2026-01-04 00:09:31.584285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '38f2639f5e8f'
down_revision: Union[str, None] = 'd92307c7b838'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Добавляем ai_analysis в student_task, если ещё не добавлена
    if not column_exists('student_task', 'ai_analysis'):
        op.add_column('student_task', sa.Column('ai_analysis', sa.Text(), nullable=True))

    # Добавляем enable_ai_analysis в tasks, если ещё не добавлена
    if not column_exists('tasks', 'enable_ai_analysis'):
        op.add_column(
            'tasks',
            sa.Column('enable_ai_analysis', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        op.alter_column('tasks', 'enable_ai_analysis', server_default=None)


def downgrade() -> None:
    # Удаляем только если колонки существуют (Alembic и так проверяет, но на всякий случай)
    if column_exists('tasks', 'enable_ai_analysis'):
        op.drop_column('tasks', 'enable_ai_analysis')
    if column_exists('student_task', 'ai_analysis'):
        op.drop_column('student_task', 'ai_analysis')