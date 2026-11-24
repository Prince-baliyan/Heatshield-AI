# Local PostgreSQL Setup (No Docker)

> **ARCHIVED — SUPERSEDED:** This document describes the previous PostgreSQL setup.
> The current project database is MySQL 8.0. Do not use these instructions for new
> development environments. Refer to [Local MySQL Setup](LOCAL_MYSQL_SETUP.md).

**Selected approach:** Install and run PostgreSQL directly on each developer machine.

**Important:** Commands below are a common Ubuntu/Debian workflow. Confirm the distribution and package version before running them. Do not use these commands unchanged on Windows, macOS, Arch, or other distributions.

## 1. Confirm operating system

```bash
cat /etc/os-release
```

Use the official PostgreSQL installation instructions for the detected distribution. Avoid adding an external repository unless the team has a specific supported-version requirement.

## 2. Install packages

On Ubuntu/Debian systems where the distribution repository provides PostgreSQL:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

Check service status:

```bash
sudo systemctl status postgresql
```

If it is not running:

```bash
sudo systemctl enable --now postgresql
```

Check client/server version:

```bash
psql --version
```

## 3. Create a development role and database

Open the PostgreSQL shell as the local administrative account:

```bash
sudo -u postgres psql
```

Run the following SQL, replacing the example password with a strong local-only password:

```sql
CREATE ROLE heatshield_dev WITH LOGIN PASSWORD 'REPLACE_WITH_LOCAL_PASSWORD';
CREATE DATABASE heatshield_ai OWNER heatshield_dev;
\q
```

Do not use the example password in a shared or production environment.

## 4. Verify connection

```bash
psql -h 127.0.0.1 -U heatshield_dev -d heatshield_ai
```

Enter the local password when prompted. Then run:

```sql
SELECT current_database(), current_user, version();
\q
```

If the connection fails, inspect the PostgreSQL service, authentication configuration, port, and credentials. Do not solve connection errors by exposing PostgreSQL to the public network.

## 5. Backend environment

Use the variables in `backend/.env.example`:

```env
DATABASE_NAME=heatshield_ai
DATABASE_USER=heatshield_dev
DATABASE_PASSWORD=your-local-password
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
```

The backend must load these values from the local environment file. Never commit the actual `.env` file.

## 6. Database safety

- Use a separate local development database.
- Do not use production credentials for development.
- Do not expose port `5432` publicly.
- Back up only data that the team is permitted to store.
- Do not commit database dumps.
- Use Django migrations for schema changes.
- Keep synthetic fixtures separate from verified observations.

## 7. PostGIS decision gate

Do not install PostGIS at this stage. Revisit only if:
- Verified polygon geometry is available and legally usable; and
- The application requires spatial queries, polygon containment, or spatial joins.

If the MVP only displays an area list or uses non-spatial identifiers, ordinary PostgreSQL is sufficient.
