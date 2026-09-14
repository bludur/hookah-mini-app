"""Add normalized unique collection names, ownership indexes and rating constraint."""
import unicodedata
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text('SELECT id, user_id, name FROM tobaccos ORDER BY id')).mappings().all()
    seen, normalized = {}, {}
    # Preflight before DDL, including on SQLite. Never silently discard user records.
    for row in rows:
        value = unicodedata.normalize('NFKC', row['name']).strip().casefold()
        if not 2 <= len(row['name'].strip()) <= 100 or len(value) > 300:
            raise RuntimeError(f"Invalid legacy tobacco name, id={row['id']}; correct it before migration")
        key = (row['user_id'], value)
        if key in seen:
            raise RuntimeError(f"Duplicate tobacco ids {seen[key]} and {row['id']}; resolve before migration")
        seen[key], normalized[row['id']] = row['id'], value
    if conn.execute(sa.text('SELECT id FROM mixes WHERE rating NOT IN (-1,0,1) LIMIT 1')).first():
        raise RuntimeError('Invalid legacy ratings; correct before migration')
    for table in ('tobaccos', 'mixes'):
        if conn.execute(sa.text(f'SELECT t.id FROM {table} t LEFT JOIN users u ON t.user_id=u.id WHERE u.id IS NULL LIMIT 1')).first():
            raise RuntimeError(f'Orphan user reference in {table}; correct before migration')
    if conn.execute(sa.text('SELECT t.id FROM tobaccos t LEFT JOIN categories c ON t.category_id=c.id WHERE t.category_id IS NOT NULL AND c.id IS NULL LIMIT 1')).first():
        raise RuntimeError('Orphan category references; correct before migration')
    op.add_column('tobaccos', sa.Column('normalized_name', sa.String(300), nullable=True))
    for tobacco_id, value in normalized.items():
        conn.execute(sa.text('UPDATE tobaccos SET normalized_name=:value WHERE id=:id'), {'value': value, 'id': tobacco_id})
    with op.batch_alter_table('tobaccos') as batch:
        batch.alter_column('normalized_name', existing_type=sa.String(300), nullable=False)
        batch.create_unique_constraint('uq_tobacco_owner_name', ['user_id', 'normalized_name'])
        batch.create_index('ix_tobaccos_user_id', ['user_id'])
    with op.batch_alter_table('mixes') as batch:
        batch.create_check_constraint('ck_mix_rating', 'rating IN (-1, 0, 1)')
        batch.create_index('ix_mixes_user_created', ['user_id', 'created_at'])


def downgrade():
    with op.batch_alter_table('mixes') as batch:
        batch.drop_index('ix_mixes_user_created')
        batch.drop_constraint('ck_mix_rating', type_='check')
    with op.batch_alter_table('tobaccos') as batch:
        batch.drop_index('ix_tobaccos_user_id')
        batch.drop_constraint('uq_tobacco_owner_name', type_='unique')
        batch.drop_column('normalized_name')
