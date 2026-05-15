"""Add advanced choreography fields to scenes

Revision ID: 9ad04d4c4774
Revises: 2c1ca0370dce
Create Date: 2026-05-15 12:42:44.484971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ad04d4c4774'
down_revision: Union[str, Sequence[str], None] = '2c1ca0370dce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_beta_authorized', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('has_seen_onboarding', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # 2. Update jobs table (Batch mode for SQLite)
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_jobs_user_id', 'users', ['user_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_index('ix_jobs_created_at')
        batch_op.drop_index('ix_jobs_status')

    # 3. Update scenes table (Batch mode for SQLite)
    with op.batch_alter_table('scenes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('on_screen_text', sa.Text(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('svg_path', sa.String(length=512), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('draw_start_ms', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('hold_ms', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('canvas_x', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('canvas_y', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('canvas_width', sa.Integer(), nullable=False, server_default='1920'))
        batch_op.add_column(sa.Column('canvas_height', sa.Integer(), nullable=False, server_default='1080'))
        batch_op.add_column(sa.Column('layout_direction', sa.String(length=32), nullable=False, server_default='right'))
        batch_op.add_column(sa.Column('kinetic_words_json', sa.Text(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('svg_content_secondary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('svg_path_secondary', sa.String(length=512), nullable=True))
        batch_op.drop_index('ix_scenes_job_id')
        batch_op.drop_index('ix_scenes_job_scene')

    # 4. Update videos table (Batch mode for SQLite)
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_index('ix_videos_job_id')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.create_index('ix_videos_job_id', ['job_id'], unique=True)

    with op.batch_alter_table('scenes', schema=None) as batch_op:
        batch_op.create_index('ix_scenes_job_scene', ['job_id', 'scene_index'], unique=False)
        batch_op.create_index('ix_scenes_job_id', ['job_id'], unique=False)
        batch_op.drop_column('svg_path_secondary')
        batch_op.drop_column('svg_content_secondary')
        batch_op.drop_column('kinetic_words_json')
        batch_op.drop_column('layout_direction')
        batch_op.drop_column('canvas_height')
        batch_op.drop_column('canvas_width')
        batch_op.drop_column('canvas_y')
        batch_op.drop_column('canvas_x')
        batch_op.drop_column('hold_ms')
        batch_op.drop_column('draw_start_ms')
        batch_op.drop_column('svg_path')
        batch_op.drop_column('on_screen_text')

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.create_index('ix_jobs_status', ['status'], unique=False)
        batch_op.create_index('ix_jobs_created_at', ['created_at'], unique=False)
        batch_op.drop_constraint('fk_jobs_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')

    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    # ### end Alembic commands ###
