#!/bin/bash

coverage run \
    --source='.' \
    --omit='venv/*,core/migrations/*' \
        manage.py test \
			--no-logs \
            --failfast \
			--nomigrations \
            --settings=backend.test_settings

coverage html
coverage report -m
