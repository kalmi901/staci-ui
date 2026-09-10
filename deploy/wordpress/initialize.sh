#!/bin/sh
set -eu

if wp core is-installed --skip-plugins --skip-themes; then
    echo "WordPress is already installed; keeping existing users and settings."
    exit 0
fi

: "${SITE_DOMAIN:?SITE_DOMAIN is required}"
: "${WORDPRESS_ADMIN_USER:?WORDPRESS_ADMIN_USER is required}"
: "${WORDPRESS_ADMIN_PASSWORD:?WORDPRESS_ADMIN_PASSWORD is required}"
: "${WORDPRESS_ADMIN_EMAIL:?WORDPRESS_ADMIN_EMAIL is required}"

wp core install \
    --url="https://$SITE_DOMAIN" \
    --title="STACI" \
    --admin_user="$WORDPRESS_ADMIN_USER" \
    --admin_email="$WORDPRESS_ADMIN_EMAIL" \
    --admin_password="$WORDPRESS_ADMIN_PASSWORD" \
    --skip-email \
    --skip-plugins \
    --skip-themes
