from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from common.logging import get_logger
from pipeline.transformation.weather_transform import WeatherTransform

logger = get_logger(__name__, "save_parquet.log")

project_root = Path(__file__).resolve().parents[2]
parquet_dir = project_root / "data" / "parquet"


def _coerce_observation_time(raw_data: object, default: datetime) -> datetime:
    if isinstance(raw_data, dict):
        observation_time = raw_data.get("observation_time") or raw_data.get("dt")
        if observation_time is not None:
            try:
                if isinstance(observation_time, (int, float)):
                    return datetime.fromtimestamp(observation_time, tz=timezone.utc)
                if isinstance(observation_time, str):
                    return datetime.fromisoformat(observation_time.replace("Z", "+00:00"))
            except (TypeError, ValueError, OverflowError):
                pass
    return default


def _normalize_numeric_dtypes(left: pl.DataFrame, right: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Cast numeric columns to a compatible common dtype before concatenation."""
    for column in sorted(set(left.columns) | set(right.columns)):
        if column not in left.columns or column not in right.columns:
            continue

        left_type = left.schema[column]
        right_type = right.schema[column]
        if left_type == right_type:
            continue

        if left_type.is_numeric() and right_type.is_numeric():
            target = pl.Float64 if left_type.is_float() or right_type.is_float() else pl.Float64
            left = left.with_columns(pl.col(column).cast(target))
            right = right.with_columns(pl.col(column).cast(target))

    return left, right


def save_parquet(data: pl.DataFrame | dict | list[dict], city: str, source: str) -> Path | None:
    """Save transformed weather data to Parquet.

    Accepts either a ready-to-write Polars DataFrame or a raw weather payload that
    is transformed via WeatherTransform before being persisted.
    """

    if isinstance(data, pl.DataFrame):
        df = data
    elif isinstance(data, (dict, list)):
        df = WeatherTransform(data, source).transform()
    else:
        raise TypeError("data must be a Polars DataFrame or a dict/list payload")

    if not isinstance(city, str) or not city.strip():
        raise ValueError("city cannot be empty")

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source cannot be empty")

    if df.is_empty():
        logger.warning(f"No data to save for {city} ({source}). Skipping Parquet save.")
        return None

    now_utc = datetime.now(timezone.utc)
    if "city" not in df.columns:
        df = df.with_columns(pl.lit(city).alias("city"))
    if "source" not in df.columns:
        df = df.with_columns(pl.lit(source).alias("source"))
    if "observation_time" not in df.columns:
        observation_time = now_utc
        if isinstance(data, dict):
            observation_time = _coerce_observation_time(data, now_utc)
        df = df.with_columns(pl.lit(observation_time).alias("observation_time"))
    if "ingested_time" not in df.columns:
        df = df.with_columns(pl.lit(now_utc).alias("ingested_time"))

    required_columns = {"city", "source", "observation_time", "ingested_time"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns for Parquet save: {missing_columns}")

    try:
        output_dir = parquet_dir / source
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_city = city.strip().lower().replace(" ", "_")
        output_file = output_dir / f"{safe_city}.parquet"

        existing_df = pl.DataFrame()
        if output_file.exists():
            logger.info(f"Appending to existing Parquet file for {city} ({source}).")
            existing_df = pl.read_parquet(output_file)

        if existing_df.height:
            existing_df, df = _normalize_numeric_dtypes(existing_df, df)
            combined = pl.concat([existing_df, df], how="diagonal", rechunk=True)
            df = combined.unique(subset=["city", "observation_time"], keep="last", maintain_order=True)

        if "observation_time" in df.columns:
            df = df.sort("observation_time")

        df.write_parquet(output_file, compression="zstd")

        logger.info(f"Saved {df.height} record(s) to Parquet for {city} ({source}).")
        return output_file

    except Exception as exc:
        logger.error(f"Failed to save Parquet for {city} ({source}): {exc}")
        raise

