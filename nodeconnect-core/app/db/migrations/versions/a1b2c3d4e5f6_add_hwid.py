"""add hwid

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-05-28 05:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fe7796f840a4'  # Latest revision based on the list
branch_labels = None
depends_on = None


def upgrade():
    # add hwid_limit to users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hwid_limit', sa.Integer(), server_default='0', nullable=False))

    # create user_hwids table
    op.create_table('user_hwids',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('hwid_value', sa.String(length=256), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('user_hwids')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('hwid_limit')
