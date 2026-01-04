# Mango: Local-First Autonomous Agent System

A modular, multi-agent system orchestrated by a central Controller.

## Overview
Mango is designed to run locally, utilizing:
- Django for the backend
- LangGraph for agent orchestration
- Celery for asynchronous processing
- Llama-CPP for local LLM inference

## Setup
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Set up environment variables in `.env`
5. Run migrations: `python manage.py migrate`
6. Start the server: `python manage.py runserver`
