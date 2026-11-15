# syntax=docker/dockerfile:1
# PriceAction AI — Laravel backend (PHP-FPM). The same image runs the API, queue worker and scheduler.

FROM php:8.4-fpm-alpine AS base
RUN apk add --no-cache icu-libs libpq libzip fcgi \
 && apk add --no-cache --virtual .build-deps $PHPIZE_DEPS icu-dev postgresql-dev libzip-dev linux-headers \
 && docker-php-ext-install -j"$(nproc)" pdo_pgsql intl zip pcntl opcache bcmath \
 && pecl install redis \
 && docker-php-ext-enable redis \
 && apk del .build-deps \
 && rm -rf /tmp/pear
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
# FPM status/ping for container health checks (served only on the internal FPM socket)
RUN printf '[www]\nping.path = /ping\npm.status_path = /status\n' > /usr/local/etc/php-fpm.d/zz-health.conf
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD SCRIPT_NAME=/ping SCRIPT_FILENAME=/ping REQUEST_METHOD=GET cgi-fcgi -bind -connect 127.0.0.1:9000 || exit 1
WORKDIR /var/www/html

FROM base AS deps
COPY composer.json composer.lock ./
RUN --mount=type=cache,target=/root/.composer/cache \
    composer install --no-dev --no-interaction --no-progress --no-scripts --no-autoloader --prefer-dist

# Development: dev dependencies included; source is bind-mounted by compose (vendor kept in an anonymous volume)
FROM base AS dev
RUN mv "$PHP_INI_DIR/php.ini-development" "$PHP_INI_DIR/php.ini"
COPY composer.json composer.lock ./
RUN --mount=type=cache,target=/root/.composer/cache \
    composer install --no-interaction --no-progress --no-scripts --prefer-dist
COPY . .
RUN composer dump-autoload && php artisan package:discover --ansi && chown -R www-data:www-data storage bootstrap/cache

FROM base AS runtime
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
COPY --from=deps /var/www/html/vendor ./vendor
COPY . .
RUN composer dump-autoload --optimize --classmap-authoritative --no-dev \
 && php artisan package:discover --ansi \
 && rm -f /usr/bin/composer \
 && chown -R www-data:www-data storage bootstrap/cache
USER www-data
CMD ["php-fpm"]
