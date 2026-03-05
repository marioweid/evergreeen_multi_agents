"""Evergreen Multi-Agent System."""

from __future__ import annotations

import os

import google.auth
from dotenv import find_dotenv, load_dotenv

from . import agent

load_dotenv(find_dotenv())
