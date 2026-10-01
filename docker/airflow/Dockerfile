FROM apache/airflow:2.10.5-python3.12

USER root
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --chown=airflow:root pyproject.toml README.md /opt/flightops/
COPY --chown=airflow:root configs /opt/flightops/configs
COPY --chown=airflow:root sql /opt/flightops/sql
COPY --chown=airflow:root src /opt/flightops/src
USER airflow
RUN pip install --no-cache-dir /opt/flightops
