"""add position to tasks

Revision ID: a7f4c3d9e8b1
Revises: f471720275db
Create Date: 2026-04-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7f4c3d9e8b1'
down_revision: Union[str, Sequence[str], None] = 'f471720275db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tasks', sa.Column('position', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE tasks
        SET position = (
            SELECT COUNT(*)
            FROM tasks AS earlier_tasks
            WHERE earlier_tasks.user_id = tasks.user_id
              AND earlier_tasks.id <= tasks.id
        )
        """
    )
    op.alter_column('tasks', 'position', existing_type=sa.Integer(), nullable=False)
    op.create_unique_constraint('uq_tasks_user_position', 'tasks', ['user_id', 'position'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_tasks_user_position', 'tasks', type_='unique')
    op.drop_column('tasks', 'position')
