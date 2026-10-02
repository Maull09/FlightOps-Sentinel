FROM apache/airflow:slim-3.3.1-python3.12

USER root
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libexpat1 libgomp1 libpcre2-8-0 libssh2-1 \
    && rm -rf /var/lib/apt/lists/*
COPY --chown=airflow:root pyproject.toml README.md /opt/flightops/
COPY --chown=airflow:root configs /opt/flightops/configs
COPY --chown=airflow:root sql /opt/flightops/sql
COPY --chown=airflow:root src /opt/flightops/src
USER airflow
RUN pip install --no-cache-dir --upgrade \
    "GitPython>=3.1.60,<4" \
    "PyJWT>=2.14,<3" \
    "aiohttp>=3.14.3,<4" \
    "apache-airflow-providers-fab>=3,<4" \
    "apache-airflow-providers-standard>=1,<2" \
    "sqlparse>=0.6,<1" \
    "tornado>=6.5.9,<7" \
    "urllib3>=2.8,<3" \
    "virtualenv>=21.7.13,<22" \
    /opt/flightops
