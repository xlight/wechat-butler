#!/bin/bash
set -e

if [ ! -f /app/config.yaml ]; then
    cp /app/config.yaml.template /app/config.yaml
fi

exec butler --config /app/config.yaml
