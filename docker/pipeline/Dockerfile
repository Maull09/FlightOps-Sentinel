FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY configs /app/configs
COPY scripts /app/scripts
COPY sql /app/sql
COPY src /app/src

RUN pip install --no-cache-dir .

CMD ["python", "scripts/train-candidates.py", "configs/training/logistic.yaml"]
