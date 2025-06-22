from alembic import op
import sqlalchemy as sa

def upgrade():
    """Create the PerformanceMetrics table."""
    op.create_table(
        'PerformanceMetrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('portfolio', sa.String(50), nullable=False),
        sa.Column('one_day_return', sa.DECIMAL(10,6)),
        sa.Column('one_week_return', sa.DECIMAL(10,6)),
        sa.Column('one_month_return', sa.DECIMAL(10,6)),
        sa.Column('ytd_return', sa.DECIMAL(10,6)),
        sa.Column('one_year_return', sa.DECIMAL(10,6)),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('date', 'portfolio', name='unique_date_portfolio')
    )

def downgrade():
    """Remove the PerformanceMetrics table."""
    op.drop_table('PerformanceMetrics') 