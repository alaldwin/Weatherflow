
FROM apache/airflow:slim-2.10.5-python3.12

USER airflow

COPY airflow/requirements.txt /tmp/requirements.txt

# Install the existing Weatherflow pipeline dependencies.
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    "apache-airflow==2.10.5" \
    -r /tmp/requirements.txt

# Install dbt separately without changing the Airflow version.
RUN python -m venv /home/airflow/dbt-venv \
    && /home/airflow/dbt-venv/bin/pip install --no-cache-dir \
        "dbt-core==1.12.5" \
        "dbt-postgres==1.11.0" \
    && /home/airflow/dbt-venv/bin/dbt --version

# Verify that the required CLIs are available.
RUN pip check