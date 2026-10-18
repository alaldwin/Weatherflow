

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from common.logging import get_logger


logger = get_logger(__name__, "airflow_dags.log")


def run_weather_pipeline():
    logger.info("Starting WeatherFlow pipeline task")

    try:

        logger.debug("Importing pipeline.main")

        from pipeline.main import main

        logger.debug("Successfully imported pipeline.main")
        logger.info("Executing WeatherFlow ingestion and PostgreSQL pipeline")

        result = main()

        logger.debug("Weather pipeline returned exit code: %s", result)

        if result != 0:
            logger.warning(
                "Weather pipeline returned a non-zero exit code: %s",
                result,
            )

            raise RuntimeError(
                f"Weather pipeline failed with exit code {result}"
            )

        logger.info("WeatherFlow pipeline completed successfully")
        return result

    except Exception:
        logger.exception("WeatherFlow pipeline task failed")
        raise  


with DAG(
    dag_id="weather_pipeline",
    description="Run the WeatherFlow ingestion and PostgreSQL pipeline",
    start_date=datetime(2026, 10, 1),
    schedule="0 * * * *",
    catchup=False,
    default_args={
        "owner": "weatherflow",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["weather", "etl", "postgres"],
) as dag:

    run_pipeline = PythonOperator(
        task_id="run_weather_pipeline",
        python_callable=run_weather_pipeline,
    )
