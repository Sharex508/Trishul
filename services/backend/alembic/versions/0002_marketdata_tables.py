"""add candle, orderbook, and feature tables

Revision ID: 0002_marketdata_tables
Revises: 0001_initial
Create Date: 2026-01-01 00:00:00

"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_marketdata_tables"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint("uq_candle_symbol_tf_ts", "candles", ["symbol", "timeframe", "ts"])
    op.create_index("ix_candles_symbol", "candles", ["symbol"])
    op.create_index("ix_candles_timeframe", "candles", ["timeframe"])
    op.create_index("ix_candles_ts", "candles", ["ts"])

    op.create_table(
        "orderbook_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("bids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("asks_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("imbalance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("spread", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ts", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_orderbook_snapshots_symbol", "orderbook_snapshots", ["symbol"])
    op.create_index("ix_orderbook_snapshots_ts", "orderbook_snapshots", ["ts"])

    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("feature_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("ts", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint("uq_feature_symbol_tf_ts", "features", ["symbol", "timeframe", "ts"])
    op.create_index("ix_features_symbol", "features", ["symbol"])
    op.create_index("ix_features_timeframe", "features", ["timeframe"])
    op.create_index("ix_features_ts", "features", ["ts"])


def downgrade() -> None:
    op.drop_index("ix_features_ts", table_name="features")
    op.drop_index("ix_features_timeframe", table_name="features")
    op.drop_index("ix_features_symbol", table_name="features")
    op.drop_constraint("uq_feature_symbol_tf_ts", "features", type_="unique")
    op.drop_table("features")

    op.drop_index("ix_orderbook_snapshots_ts", table_name="orderbook_snapshots")
    op.drop_index("ix_orderbook_snapshots_symbol", table_name="orderbook_snapshots")
    op.drop_table("orderbook_snapshots")

    op.drop_index("ix_candles_ts", table_name="candles")
    op.drop_index("ix_candles_timeframe", table_name="candles")
    op.drop_index("ix_candles_symbol", table_name="candles")
    op.drop_constraint("uq_candle_symbol_tf_ts", "candles", type_="unique")
    op.drop_table("candles")
