#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="$PWD:$PYTHONPATH"
gunicorn main:app -b 0.0.0.0:8000