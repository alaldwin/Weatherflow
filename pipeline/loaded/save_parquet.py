from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from common.logging import get_logger
from pipeline.transformation.weather_transform import WeatherTransform


logger = get_logger(__name__, "save_parquet.log")

project_root = Path(__file__).resolve().parents[2]
parquet_dir = project_root / "data" / "parquet"


def _normalize_observation_time(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize observation_time to a UTC Datetime column."""

    column = "observation_time" 

    if column not in df.columns or df.is_empty(): 
        return df 

    dtype = df.schema[column] 

    if dtype.is_numeric(): 
        # OpenWeather dt values are Unix timestamps in seconds. 
        df = df.with_columns( 
            pl.from_epoch( 
                pl.col(column).cast(pl.Int64), 
                time_unit="s", 
                ) 
                .dt.replace_time_zone("UTC") 
                .alias(column) 
            ) 

    elif dtype == pl.String: 
        df = df.with_columns( 
            pl.col(column) 
            .str.to_datetime(time_zone="UTC", strict=False) 
            .alias(column) 
        ) 

    elif isinstance(dtype, pl.Datetime): 
        if dtype.time_zone is None: 
            df = df.with_columns( 
                pl.col(column) 
                .dt.replace_time_zone("UTC") 
                .alias(column) 
            ) 

        else: 
            df = df.with_columns( 
                pl.col(column) 
                .dt.convert_time_zone("UTC") 
                .alias(column) 
            ) 

    return df


def _normalize_numeric_dtypes(left: pl.DataFrame, right: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Cast numeric columns to a compatible common dtype before concatenation."""

    for column in sorted(set(left.columns) & set(right.columns)):
        if column not in left.columns or column not in right.columns:
            continue

        left_type = left.schema[column]
        right_type = right.schema[column]

        if left_type == right_type:
            continue

        if left_type.is_numeric() and right_type.is_numeric(): 
            left = left.with_columns( 
                pl.col(column).cast(pl.Float64) 
            ) 
            right = right.with_columns( 
                pl.col(column).cast(pl.Float64) 
            ) 

    return left, right


def save_parquet(data: pl.DataFrame | dict | list[dict], city: str, source: str) -> Path | None:
    """Save transformed weather data to Parquet.

    Accepts either a ready-to-write Polars DataFrame or a raw weather payload that
    is transformed via WeatherTransform before being persisted.
    """

    if not isinstance(city, str) or not city.strip(): 
        raise ValueError("city cannot be empty") 
    if not isinstance(source, str) or not source.strip(): 
        raise ValueError("source cannot be empty")

    city = city.strip() 
    source = source.strip()

    if isinstance(data, pl.DataFrame): 
        df = data
        
    elif isinstance(data, (dict, list)): 
        df = WeatherTransform(data, source).transform() 
    else: 
        raise TypeError( "data must be a Polars DataFrame or a dict/list payload" )

    if df.is_empty(): 
        logger.warning( "No data to save for %s (%s). Skipping.", city, source )

        return None

    now_utc = datetime.now(timezone.utc)

    # Ensure metadata columns exist.
    if "city" not in df.columns:
        df = df.with_columns(pl.lit(city).alias("city"))

    if "source" not in df.columns:
        df = df.with_columns(pl.lit(source).alias("source"))

    if "observation_time" not in df.columns:
        df = df.with_columns(pl.lit(now_utc).cast(pl.Datetime("us", "UTC")).alias("observation_time"))

    if "ingested_time" not in df.columns:
        df = df.with_columns(
            pl.lit(now_utc)
            .cast(pl.Datetime("us", "UTC"))
            .alias("ingested_time")
        )

    if "observation_time" in df.columns:
        df = df.with_columns(
            pl.col("observation_time").fill_null(pl.col("ingested_time")).alias("observation_time")
        )

    # Normalize timestamps before combining old and new data.
    df = _normalize_observation_time(df)

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

            # Normalize historical timestamps and add metadata if absent.
            if "source" not in existing_df.columns:
                existing_df = existing_df.with_columns(pl.lit(source).alias("source"))

            if "city" not in existing_df.columns:
                existing_df = existing_df.with_columns(pl.lit(city).alias("city"))

            existing_df = _normalize_observation_time(existing_df)

            if "ingested_time" not in existing_df.columns:
                existing_df = existing_df.with_columns(pl.lit(now_utc).cast(pl.Datetime("us", "UTC")).alias("ingested_time"))

            if "observation_time" in existing_df.columns:
                existing_df = existing_df.with_columns(
                    pl.col("observation_time").fill_null(pl.col("ingested_time")).alias("observation_time")
                )

        existing_df, df = _normalize_numeric_dtypes(existing_df, df)

        if existing_df.is_empty():
            combined = df
        else:
            # Preserve columns that exist in either schema.
            combined = pl.concat([existing_df, df], how="diagonal_relaxed", rechunk=True)

        # Keep the newest ingested record for each observation.
        df = ( combined .sort("ingested_time") .unique( subset=["city", "source", "observation_time"], keep="last", maintain_order=True, ) )

        if "observation_time" in df.columns:
            df = df.sort("observation_time")

        df.write_parquet(output_file, compression="zstd")

        logger.info(f"Saved {df.height} record(s) to Parquet for {city} ({source}).")
        return output_file

    except Exception as exc:
        logger.error(f"Failed to save Parquet for {city} ({source}): {exc}")
        raise

