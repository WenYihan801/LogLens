#!/bin/sh
# Runs once when the Postgres volume is first created: adds a separate database
# for the integration tests so they never touch your development data.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
  CREATE DATABASE ${POSTGRES_DB}_test OWNER "$POSTGRES_USER";
SQL
