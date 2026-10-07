FROM python:3.14-slim

# Working directory for the application
WORKDIR /app

# environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1

# System Dependencies
COPY requirements.txt /app/requirements.txt

# 
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \ 
		libpq5 \
	&& pip install --no-cache-dir -r /app/requirements.txt \ 
	&& rm -rf /var/lib/apt/lists/*

COPY . .

# Run as a module so the pipeline/common/config packages resolve correctly.
CMD ["python", "-m", "pipeline.main"]