from pathlib import Path

import polars as pl

from common.logging import get_logger

logger = get_logger(__name__, "save_parquet.log")


def save_parquet(df: pl.DataFrame, city: str, source: str) -> None:

    """Save the Polars DataFrame as a Parquet file."""

    try:
        output_dir = Path("data/parquet") / source
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{city}.parquet"

        if output_file.exists():
            existing_df = pl.read_parquet(output_file)
            df = pl.concat([existing_df, df], how="vertical", rechunk=True)
            df = df.unique(subset=df.columns, keep="last")

        df.write_parquet(output_file)

        logger.info(f"Saved Parquet file for {city} from {source} at {output_file}")

    except Exception as e:
        logger.error(f"Error saving Parquet file for {city} from {source}: {e}")
        raise

