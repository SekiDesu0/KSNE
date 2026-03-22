#!/bin/bash

git pull
docker build -t rendiciones:latest .
docker compose up -d