SELECT 'CREATE DATABASE notification_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'notification_db')\gexec

SELECT 'CREATE DATABASE route_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'route_db')\gexec
