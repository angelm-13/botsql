# Maintenance generado

## Configuración inicial

```bash
cd maintenance
cp maintenance.env.example maintenance.env
chmod +x *.sh
```

Edita `maintenance.env` con los datos reales de PostgreSQL y rutas.

## Backup

```bash
./backup_postgres.sh
```

## Restore

```bash
./restore_postgres.sh ./backups/tyakxa_pg_tyakxa_erp_YYYYMMDD_HHMMSS.dump
```

## Rotación

```bash
./rotate_backups.sh
```

## Healthcheck

```bash
./healthcheck.sh
```

## Mantenimiento DB

```bash
./vacuum_analyze.sh
```

## Cron

Edita `crontab.example`, reemplaza rutas absolutas y luego:

```bash
crontab crontab.example
```
