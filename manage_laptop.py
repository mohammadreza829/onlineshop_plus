#!/usr/bin/env python
"""Local-only Django entrypoint; leaves manage.py and production .env unchanged."""

import os
import sys

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "onlineshop.laptop_settings"
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
