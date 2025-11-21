FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=2.2.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates libopenblas-dev libomp-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry via pip
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

WORKDIR /code

# Copy poetry files
COPY pyproject.toml poetry.lock* /code/

# Install dependencies using Poetry
RUN poetry install --no-root --only main --no-interaction --no-ansi

# Copy project sources
COPY . /code

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
