# Local MySQL 8.4 LTS setup

This runbook implements `STORAGE-001` through `STORAGE-004`, `MYSQL-001` through `MYSQL-004`, and `TEST-038` for a private local deployment. It does not authorize a public database or application listener.

## Verified distribution

Issue #68 was validated with MySQL Community Server 8.4.10 LTS for Windows x86-64. Oracle's live download page listed `mysql-8.4.10-winx64.msi`, 129.9 MB, MD5 `4534e93ee4a031e1c6e082a0bf5ac945`. The downloaded MSI matched that checksum and had a valid Windows signature from Oracle America, Inc.

Oracle's Windows manual recommends the MSI and MySQL Configurator, requires the Microsoft Visual C++ 2019 redistributable, and documents `C:\Program Files\MySQL\MySQL Server 8.4` as the default MSI location. The local service must be configured with an option file that contains both `bind-address=127.0.0.1` and `mysqlx-bind-address=127.0.0.1` before its first start. Do not add Windows Firewall rules for ports 3306 or 33060.

Official references:

- <https://dev.mysql.com/downloads/mysql/8.4.html>
- <https://dev.mysql.com/doc/refman/8.4/en/windows-installation.html>

## Secret boundary

Generate separate strong root and application passwords. Store them outside the checkout in a current-user-only directory such as `%LOCALAPPDATA%\VirtualCasinoSimulator\secrets`. The application environment file uses these names:

```text
CASINO_STORAGE_PROVIDER=mysql
CASINO_MYSQL_HOST=127.0.0.1
CASINO_MYSQL_PORT=3306
CASINO_MYSQL_USER=casino_app
CASINO_MYSQL_PASSWORD=<generated-app-password>
CASINO_MYSQL_DATABASE=virtual_casino
```

Never pass a password as a command-line argument or copy the real environment file into a deployment. Load it into the process environment immediately before starting the copied deployment. The repository ignores local `.env` files while retaining `.env.example` and `.env.*.example` samples.

## Server option file

Create the service option file outside Git before installing or starting the service. Replace only the installation and data paths if a non-default MSI layout is used.

```ini
[mysqld]
basedir=C:/Program Files/MySQL/MySQL Server 8.4
datadir=C:/ProgramData/MySQL/MySQL Server 8.4/Data
port=3306
mysqlx_port=33060
bind-address=127.0.0.1
mysqlx-bind-address=127.0.0.1
skip_name_resolve=ON
local_infile=OFF
secure_file_priv=NULL
general_log=OFF
slow_query_log=OFF
log_bin=OFF
```

Initialize the data directory without starting a wildcard listener, install the `MySQL84` Windows service with `--defaults-file=<external-option-file>`, and run it under the service account selected by the MSI tooling. Confirm `Get-NetTCPConnection` reports only `127.0.0.1:3306` and `127.0.0.1:33060` before creating accounts.

## Database and least-privilege account

Connect locally as root using a defaults file or standard-input prompt. Create `virtual_casino` with `utf8mb4`, create `casino_app` only for host `127.0.0.1`, and grant only `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, and `REFERENCES` on `virtual_casino.*`. `CREATE` and `REFERENCES` are required because the provider performs idempotent fresh-schema bootstrap including its ledger foreign key. Do not grant global privileges, `GRANT OPTION`, `FILE`, `PROCESS`, `SHUTDOWN`, or user-management privileges.

Load the external application environment, install the optional driver in an isolated environment with `python -m pip install -e ".[mysql]"`, then run:

```powershell
python tests/run_tests.py --mysql-live
```

The live case resets only the dedicated application database, bootstraps schema and seed players, persists users, sessions, terms state, player records, game state, settings documents, history, autoplay sessions, and bot profiles, and applies concurrent debits to prove row-locking behavior. The service-free `--storage` case separately proves JSON fallback and schema shape.

## Restart and exposure proof

After the live case, stop and start the `MySQL84` service, rebuild the application provider by restarting the copied deployment, and verify the integration user session, player balance, ledger events, saved game state, bot profile, and autoplay session remain present. Record only counts and identifiers created for the test; never record session tokens or passwords.

Before handoff, confirm:

- `SHOW GRANTS FOR 'casino_app'@'127.0.0.1'` is database-scoped.
- Ports 3306 and 33060 listen only on `127.0.0.1`.
- No enabled inbound firewall rule was added for MySQL.
- `CASINO_STORAGE_PROVIDER` absent still selects JSON and passes `--storage`.
- `git status --ignored` shows real secret files are outside the checkout and no key, `.env`, Terraform state, or credential material is staged.
