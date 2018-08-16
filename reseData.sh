#!/bin/bash

set -ex

rm /var/lib/zyhr/db.sqlite3 || true
./manage.py migrate
./manage.py prepareData
