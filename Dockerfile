FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN apt-get update \
	&& apt-get install -y --no-install-recommends gcc libpq-dev \
	&& pip install --no-cache-dir -r /app/requirements.txt \
	&& apt-get remove -y gcc \
	&& apt-get autoremove -y \
	&& rm -rf /var/lib/apt/lists/*

COPY . /app

CMD ["python","-u","pipeline/main.py"]
