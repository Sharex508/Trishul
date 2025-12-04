"""initial unified schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-12-02 21:20:00

"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'symbols',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=32), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_symbols_name', 'symbols', ['name'])

    op.create_table(
        'prices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('symbol_id', sa.Integer(), sa.ForeignKey('symbols.id'), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_prices_ts', 'prices', ['ts'])
    op.create_unique_constraint('uq_price_symbol_ts', 'prices', ['symbol_id', 'ts'])

    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('symbol_id', sa.Integer(), sa.ForeignKey('symbols.id'), nullable=False),
        sa.Column('side', sa.String(length=4), nullable=False),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='FILLED'),
        sa.Column('ts', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('symbol_id', sa.Integer(), sa.ForeignKey('symbols.id'), nullable=False, unique=True),
        sa.Column('qty', sa.Float(), nullable=False, server_default='0'),
        sa.Column('avg_price', sa.Float(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'ai_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('symbol_id', sa.Integer(), sa.ForeignKey('symbols.id'), nullable=False),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0'),
        sa.Column('rationale', sa.String(length=1024), nullable=False, server_default=''),
        sa.Column('ts', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'api_credentials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('provider', sa.String(length=32), nullable=False, unique=True),
        sa.Column('key_encrypted', sa.String(length=512), nullable=False),
        sa.Column('secret_encrypted', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_api_credentials_provider', 'api_credentials', ['provider'])


def downgrade() -> None:
    op.drop_index('ix_api_credentials_provider', table_name='api_credentials')
    op.drop_table('api_credentials')
    op.drop_table('ai_logs')
    op.drop_table('positions')
    op.drop_table('orders')
    op.drop_index('ix_prices_ts', table_name='prices')
    op.drop_constraint('uq_price_symbol_ts', 'prices', type_='unique')
    op.drop_table('prices')
    op.drop_index('ix_symbols_name', table_name='symbols')
    op.drop_table('symbols')
