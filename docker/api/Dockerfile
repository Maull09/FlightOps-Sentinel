FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 libpcre2-8-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY configs /app/configs
COPY src /app/src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "flightops.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
