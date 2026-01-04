# Mango: Local-First Autonomous Agent System

A modular, multi-agent system orchestrated by a central Controller.

## Overview
Mango is designed to run locally, utilizing:
- Django for the backend
- LangGraph for agent orchestration
- Celery for asynchronous processing
- Llama-CPP for local LLM inference

## Setup
1. Install `uv` if not already installed.
2. Initialize environment: `uv venv`
3. Activate it: `venv\Scripts\activate` (Windows)
4. Install dependencies: `uv pip install -r requirements.txt`
5. Set up environment variables in `.env`
6. Run migrations: `uv run python manage.py migrate`
7. Start the server (ASGI): `uv run uvicorn config.asgi:application --reload`
