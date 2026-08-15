#!/bin/sh
set -e

cd /app

echo "**** 1/10 - Make sure /uploads folders exist ****"
mkdir -p /app/public/uploads

echo "**** 2/10 - Create the symbolic link for the /uploads folder ****"
# Skipped for dev environment because we mount it directly in docker-compose!

echo "**** 3/10 - Setting env variables ****"
rm -rf /app/.env.local
touch /app/.env.local

echo "APP_ENV=${APP_ENV:-dev}" >> "/app/.env.local"
echo "APP_DEBUG=${APP_DEBUG:-1}" >> "/app/.env.local"
echo "APP_SECRET=${APP_SECRET:-$(openssl rand -base64 21)}" >> "/app/.env.local"

echo "JWT_SECRET_KEY=${JWT_SECRET_KEY:-%kernel.project_dir%/config/jwt/private.pem}" >> "/app/.env.local"
echo "JWT_PUBLIC_KEY=${JWT_PUBLIC_KEY:-%kernel.project_dir%/config/jwt/public.pem}" >> "/app/.env.local"
echo "JWT_PASSPHRASE=${JWT_PASSPHRASE:-$(openssl rand -base64 21)}" >> "/app/.env.local"

echo "DB_DRIVER=${DB_DRIVER:-}" >> "/app/.env.local"
echo "DB_NAME=${DB_NAME:-}" >> "/app/.env.local"
echo "DB_HOST=${DB_HOST:-}" >> "/app/.env.local"
echo "DB_PORT=${DB_PORT:-}" >> "/app/.env.local"
echo "DB_USER=${DB_USER:-}" >> "/app/.env.local"
echo "DB_PASSWORD=${DB_PASSWORD:-}" >> "/app/.env.local"
echo "DB_VERSION=${DB_VERSION:-}" >> "/app/.env.local"

echo "CORS_ALLOW_ORIGIN=${CORS_ALLOW_ORIGIN:-'^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$'}" >> "/app/.env.local"

echo "SYMFONY_TRUSTED_PROXIES=${SYMFONY_TRUSTED_PROXIES:-private_ranges}" >> "/app/.env.local"
echo "SYMFONY_TRUSTED_HEADERS=${SYMFONY_TRUSTED_HEADERS:-forwarded,x-forwarded-for,x-forwarded-host,x-forwarded-proto,x-forwarded-port,x-forwarded-prefix}" >> "/app/.env.local"

echo "session.cookie_secure=${HTTPS_ENABLED}" >> /usr/local/etc/php/conf.d/php.ini
echo "date.timezone=${PHP_TZ}" >> /usr/local/etc/php/conf.d/php.ini
echo "memory_limit=${PHP_MEMORY_LIMIT:-'512M'}" >> /usr/local/etc/php/conf.d/php.ini
echo "upload_max_filesize=${UPLOAD_MAX_FILESIZE:-'20M'}" >> /usr/local/etc/php/conf.d/php.ini
echo "post_max_size=${UPLOAD_MAX_FILESIZE:-'100M'}" >> /usr/local/etc/php/conf.d/php.ini
echo "opcache.enable=0" >> /usr/local/etc/php/conf.d/php.ini

echo "**** 3.5/10 - Install PHP Dependencies ****"
composer install --no-interaction

echo "**** 4/10 - Migrate the database ****"
php bin/console doctrine:migration:migrate --no-interaction --allow-no-migration

echo "**** 5/10 - Refresh cached values ****"
php bin/console app:refresh-cached-values

echo "**** 6/10 - Create API keys ****"
php bin/console lexik:jwt:generate-keypair --skip-if-exists

echo "**** 7/10 - Create user and use PUID/PGID ****"
# Skipped for dev environment to prevent Windows permission crashes

echo "**** 8/10 - Set Permissions ****"
# Skipped for dev environment to prevent Windows permission crashes

echo "**** 9/10 - Create symfony log files ****"
mkdir -p /app/var/log
touch /app/var/log/dev.log

echo "**** 9.5/10 - Fix Web Server Paths ****"
sed -i 's|/app/public/public|/app/public|g' /etc/caddy/Caddyfile

echo "**** 10/10 - Setup complete, starting the server. ****"
LD_PRELOAD=/opt/libcurl-impersonate-ff.so CURL_IMPERSONATE=ff117 frankenphp run --config /etc/caddy/Caddyfile