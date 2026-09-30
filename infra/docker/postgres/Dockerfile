FROM postgis/postgis:16-3.4

# Install pgvector extension package on top of PostGIS 16 image
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
