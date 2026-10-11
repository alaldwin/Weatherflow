

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_weather_pipeline():
    from pipeline.main import main

    result = main()

    if result != 0:
        raise RuntimeError(
            f"Weather pipeline failed with exit code {result}"
        )


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
