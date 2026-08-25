FROM python:3.12-slim

WORKDIR /workspace
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps

RUN pip install --no-cache-dir -e ".[hosted]"

ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "nis2check_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
