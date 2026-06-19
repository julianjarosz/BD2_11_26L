FROM apache/airflow:2.10.5-python3.12

USER airflow

RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch
RUN pip install --no-cache-dir \
    "numpy>=2.0.0" \
    "scikit-learn>=1.4.0" \
    "pandas>=2.2.0" \
    "psycopg[binary]>=3.2.0" \
    "requests>=2.32.0" \
    "redis>=6.0.0" \
    "python-dotenv>=0.9.9" \
    apache-airflow-providers-docker
