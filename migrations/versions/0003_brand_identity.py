"""Treat brand and flavor together as the collection identity."""
import unicodedata
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    op.add_column('tobaccos', sa.Column('normalized_brand', sa.String(300), nullable=False, server_default=''))
    for row in conn.execute(sa.text('SELECT id, brand FROM tobaccos')).mappings().all():
        brand = unicodedata.normalize('NFKC', row['brand'] or '').strip().casefold()
        if len(brand) > 300:
            raise RuntimeError('Legacy brand is too long')
        conn.execute(sa.text('UPDATE tobaccos SET normalized_brand=:brand WHERE id=:id'), {'brand': brand, 'id': row['id']})
    with op.batch_alter_table('tobaccos') as batch:
        batch.drop_constraint('uq_tobacco_owner_name', type_='unique')
        batch.create_unique_constraint('uq_tobacco_owner_brand_name', ['user_id', 'normalized_name', 'normalized_brand'])

def downgrade():
    conn = op.get_bind()
    if conn.execute(sa.text('SELECT user_id, normalized_name FROM tobaccos GROUP BY user_id, normalized_name HAVING COUNT(*) > 1')).first():
        raise RuntimeError('Different brands share a flavor; resolve before downgrade')
    with op.batch_alter_table('tobaccos') as batch:
        batch.drop_constraint('uq_tobacco_owner_brand_name', type_='unique')
        batch.create_unique_constraint('uq_tobacco_owner_name', ['user_id', 'normalized_name'])
        batch.drop_column('normalized_brand')
