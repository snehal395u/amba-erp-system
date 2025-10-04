# alembic revision: 0001 initial
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('customers',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False)
    )
    op.create_table('products',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('sku', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('uom', sa.String(length=32)),
        sa.Column('current_stock', sa.Integer, nullable=False, server_default='0'),
        sa.Column('reorder_level', sa.Integer, server_default='0'),
        sa.Column('price', sa.Numeric(12,2), server_default='0')
    )
    op.create_table('orders',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('order_number', sa.String(length=50), nullable=False),
        sa.Column('customer_id', sa.Integer, nullable=False),
        sa.Column('order_date', sa.Date),
        sa.Column('total_amount', sa.Numeric(14,2), server_default='0'),
        sa.Column('status', sa.String(length=50), server_default='draft'),
        sa.Column('created_by', sa.String(length=255))
    )
    op.create_table('order_items',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('order_id', sa.Integer, nullable=False),
        sa.Column('product_id', sa.Integer, nullable=False),
        sa.Column('qty', sa.Integer),
        sa.Column('unit_price', sa.Numeric(12,2)),
        sa.Column('line_total', sa.Numeric(14,2))
    )
    op.create_table('inventory_log',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('product_id', sa.Integer, nullable=False),
        sa.Column('change_qty', sa.Integer),
        sa.Column('reason', sa.String(length=255)),
        sa.Column('prev_stock', sa.Integer),
        sa.Column('new_stock', sa.Integer)
    )

def downgrade():
    op.drop_table('inventory_log')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_table('customers')
