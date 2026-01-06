#!/bin/sh
set -e

host="$1"
port="$2"
shift 2
cmd="$@"

until wget --no-verbose --tries=1 --spider "http://$host:$port/-/healthy" > /dev/null 2>&1; do
  >&2 echo "Prometheus is unavailable - sleeping"
  sleep 2
done

>&2 echo "Prometheus is up - executing command"
exec $cmd

