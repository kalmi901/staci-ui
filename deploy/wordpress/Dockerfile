# Always build with --pull for PHP security updates. The version check prevents
# a cached or not-yet-rebuilt upstream image from producing a vulnerable image.
FROM wordpress:php8.3-apache AS web

COPY check-php-security.php /usr/local/lib/staci/check-php-security.php
COPY php-security.ini /usr/local/etc/php/conf.d/zz-staci-security.ini
RUN php /usr/local/lib/staci/check-php-security.php \
    && php -r 'exit(extension_loaded("session") && !ini_get("session.upload_progress.enabled") ? 0 : 1);'

FROM wordpress:cli-php8.3 AS cli

COPY check-php-security.php /usr/local/lib/staci/check-php-security.php
COPY php-security.ini /usr/local/etc/php/conf.d/zz-staci-security.ini
RUN php /usr/local/lib/staci/check-php-security.php \
    && php -r 'exit(extension_loaded("session") && !ini_get("session.upload_progress.enabled") ? 0 : 1);'
