FROM python:3.14-slim

WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt

RUN apt-get update \
	&& apt-get install -y --no-install-recommends libpq5 \
	&& pip install --no-cache-dir -r /app/requirements.txt \
	&& apt-get autoremove -y \
	&& rm -rf /var/lib/apt/lists/*

COPY . /app

# Run as a module so the pipeline/common/config packages resolve correctly.
CMD ["python", "-m", "pipeline.main"]