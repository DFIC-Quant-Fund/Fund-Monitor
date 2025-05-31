"""create performance metrics table

might need to install: pip install Flask-Migrate Flask-SQLAlchemy
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'PerformanceReturns',
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('portfolio', sa.String(50), nullable=False),
        sa.Column('one_day_return', sa.Float()),
        sa.Column('one_week_return', sa.Float()),
        sa.Column('one_month_return', sa.Float()),
        sa.Column('ytd_return', sa.Float()),
        sa.Column('one_year_return', sa.Float()),
        sa.Column('inception_return', sa.Float()),
        sa.PrimaryKeyConstraint('date', 'portfolio')
    )

def downgrade():
    op.drop_table('PerformanceReturns')

# create this new file then run the following commands to apply the migration:
# flask db init
# flask db migrate -m "create performance metrics table"
# flask db upgrade