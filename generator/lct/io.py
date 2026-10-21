"""Shared helpers: paths, config loading, seeded randomness and CSV writing."""

from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

GENERATOR_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = GENERATOR_DIR.parent
DATA_DIR = REPO_DIR / "data"
DOCS_DIR = REPO_DIR / "docs"
CHARTS_DIR = REPO_DIR / "validation" / "charts"


def load_yaml(name: str) -> dict:
    with open(GENERATOR_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rng_for(seed: int, name: str) -> np.random.Generator:
    """A separate, reproducible random stream per module.

    Each part of the generator (runs, freshness, usage...) gets its own stream
    keyed on its name. That way, changing how usage is generated does not shift
    every random number in the runs table, and stories stay put.
    """
    return np.random.default_rng([seed, zlib.crc32(name.encode())])


def write_csv(df: pd.DataFrame, table: str) -> Path:
    """Write a table to data/<table>.csv with Tableau-friendly formatting."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            # Dates without a time part are written as plain dates
            if (out[col].dropna().dt.normalize() == out[col].dropna()).all() and col in DATE_ONLY_COLUMNS:
                out[col] = out[col].dt.strftime("%Y-%m-%d")
            else:
                out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        elif pd.api.types.is_bool_dtype(out[col]):
            out[col] = out[col].map({True: "true", False: "false"})
    path = DATA_DIR / f"{table}.csv"
    out.to_csv(path, index=False)
    return path


# Columns that hold a calendar date rather than a timestamp
DATE_ONLY_COLUMNS = {"date", "week_start", "created_date", "migration_date"}
