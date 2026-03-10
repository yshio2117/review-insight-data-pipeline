FROM python:3.12-slim

# system deps for mecab-python3
RUN apt-get update && apt-get install -y --no-install-recommends \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir -r requirements.txt

COPY config/ config/
COPY dics/ dics/
COPY sql/ sql/
COPY src/ src/
COPY data/ data/

ENV PYTHONPATH=/app

# sanity check
RUN echo "こんにちは" | mecab

# run for BigQuery output
#CMD ["python", "-m", "src.reason_extraction.main", "--input-file", "data/input/sample_hotel_reviews.csv", "--output", "bigquery"]

# run for local output
CMD ["python", "-m", "src.reason_extraction.main", "--input-file", "data/input/sample_hotel_reviews.csv", "--output", "local"]