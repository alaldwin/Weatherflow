

from datetime import datetime, timedelta

from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule

from airflow.operators.python import PythonOperator

from airflow import DAG 
from common.logging import get_logger 

logger = get_logger(__name__, "airflow_dags.log") 


def run_weather_pipeline():
    logger.info("Starting WeatherFlow pipeline task")

    try: 
        from pipeline.main import main

        logger.info("Executing WeatherFlow ingestion and PostgreSQL pipeline") 
        result = main()

        logger.info("Weather pipeline returned exit code: %s", result)

        if result == 2:
            logger.error(
                "Weather API outage detected. "
                "Marking ingestion as failed; dbt will use existing records."
            )
            raise RuntimeError("Weather API outage: ingestion failed")

        if result != 0:
            raise RuntimeError(
                f"Weather pipeline failed with exit code {result}"
            )

        logger.info("WeatherFlow pipeline completed successfully")
        return result

    except Exception:
        logger.exception("WeatherFlow pipeline task failed")
        raise



default_args = {
    "owner": "weatherflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}



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

    run_dbt_build = BashOperator(
        task_id="run_dbt_build",
        bash_command=(
            "/home/airflow/dbt-venv/bin/dbt build "
            "--project-dir /opt/weatherflow/dbt_weatherflow "
            "--profiles-dir /opt/weatherflow/dbt_weatherflow "
            "--target dev"
        ),
        retries=2,
        retry_delay=timedelta(minutes=2),
        trigger_rule=TriggerRule.ALL_DONE,
    )

    run_pipeline >> run_dbt_build