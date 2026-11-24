
# Local MySQL Setup (No Docker)

**Selected approach:** Install and run MySQL Server 8.0 directly on the developer machine.

**Verified project environment:**
- MySQL Server: 8.0.46
- Database: `heatshield_ai`
- Development user: `heatshield_dev`
- Host: `127.0.0.1`
- Port: `3306`
- Django driver: `mysqlclient`

## 1. Confirm operating system

```bash
cat /etc/os-release
```

Use installation instructions appropriate for the detected Linux distribution.

## 2. Install and verify MySQL

On Ubuntu/Debian systems:

```bash
sudo apt update
sudo apt install mysql-server
```

Check service status:

```bash
sudo systemctl status mysql
```

Start and enable the service if required:

```bash
sudo systemctl enable --now mysql
```

Check client version:

```bash
mysql --version
```

## 3. Create the development database and user

Open the local administrative MySQL shell:

```bash
sudo mysql
```

Execute the following SQL, replacing the placeholder with a strong local-only password:

```sql
CREATE DATABASE heatshield_ai
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER 'heatshield_dev'@'localhost'
IDENTIFIED BY 'REPLACE_WITH_LOCAL_PASSWORD';

GRANT ALL PRIVILEGES ON heatshield_ai.*
TO 'heatshield_dev'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

If the database or user already exists, inspect the existing configuration instead of repeating these commands.

## 4. Verify the database connection

```bash
mysql -u heatshield_dev -p -h 127.0.0.1 -D heatshield_ai
```

Enter the local password when prompted.

```sql
SELECT DATABASE(), CURRENT_USER(), VERSION();
EXIT;
```

Do not expose MySQL port 3306 publicly to solve local connection problems.

## 5. Backend environment

Configure `backend/.env` using `backend/.env.example`:

```env
DATABASE_NAME=heatshield_ai
DATABASE_USER=heatshield_dev
DATABASE_PASSWORD=your-local-password
DATABASE_HOST=127.0.0.1
DATABASE_PORT=3306
```

Never commit the actual `.env` file or share its contents.

## 6. Django database configuration

The Django database engine must use:

```python
"ENGINE": "django.db.backends.mysql"
```

The backend dependency must include `mysqlclient`.

Verify the backend connection:

```bash
cd backend
source .venv/bin/activate
python manage.py check
python manage.py shell -c 'from django.db import connection; connection.ensure_connection(); print("MySQL connection successful")'
```

Run migrations only after application models are defined and reviewed:

```bash
python manage.py migrate
```

## 7. Database safety

- Use a separate local development database.
- Never use production credentials for development.
- Keep database credentials outside source control.
- Do not expose port 3306 publicly.
- Back up only data the team is permitted to store.
- Do not commit database dumps.
- Use Django migrations for schema changes.
- Keep synthetic fixtures separate from verified observations.

## 8. Spatial data decision

MySQL 8.0 supports spatial data types and functions.

Start with representative latitude/longitude coordinates if they satisfy MVP requirements.

Consider MySQL spatial columns and queries only when verified polygon boundaries, spatial joins, or point-in-polygon operations are required.

PostGIS is PostgreSQL-specific and is not part of this MySQL architecture.
