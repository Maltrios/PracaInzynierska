#!/bin/bash
set -e

printenv | sed 's/^\([^=]*\)=\(.*\)$/export \1="\2"/' > /etc/profile.d/container_env.sh
chmod +x /etc/profile.d/container_env.sh

touch /var/log/cleanup.log

cron -f
