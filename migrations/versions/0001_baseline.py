"""Create the original schema or adopt a complete pre-Alembic installation."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names()) & {'users', 'categories', 'tobaccos', 'mixes'}
    if tables:
        required = {'users': {'id', 'telegram_id', 'username', 'first_name', 'created_at'},
                    'categories': {'id', 'name', 'emoji', 'taste_profile'},
                    'tobaccos': {'id', 'user_id', 'name', 'brand', 'category_id', 'notes', 'created_at'},
                    'mixes': {'id', 'user_id', 'name', 'components', 'description', 'tips', 'rating', 'is_favorite', 'request_type', 'created_at'}}
        if tables != set(required) or any(not columns <= {c['name'] for c in inspector.get_columns(table)} for table, columns in required.items()):
            raise RuntimeError('Unknown legacy schema. Back up and inspect the database before migration.')
        return
    op.create_table('users', sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
                    sa.Column('username', sa.String()), sa.Column('first_name', sa.String()),
                    sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True)
    op.create_table('categories', sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('name', sa.String(), nullable=False, unique=True),
                    sa.Column('emoji', sa.String(), nullable=False), sa.Column('taste_profile', sa.String(), nullable=False))
    op.create_table('tobaccos', sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
                    sa.Column('name', sa.String(), nullable=False), sa.Column('brand', sa.String()),
                    sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id')),
                    sa.Column('notes', sa.Text()), sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_table('mixes', sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
                    sa.Column('name', sa.String(), nullable=False), sa.Column('components', sa.JSON(), nullable=False),
                    sa.Column('description', sa.Text()), sa.Column('tips', sa.Text()), sa.Column('rating', sa.Integer()),
                    sa.Column('is_favorite', sa.Boolean(), nullable=False), sa.Column('request_type', sa.String(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False))


def downgrade():
    raise RuntimeError('Baseline downgrade would delete user data; restore a verified backup instead.')
