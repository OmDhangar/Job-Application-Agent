# 1. Infrastructure
docker-compose up -d db redis rabbitmq

# 2. Pull local model (run once, ~4GB)
ollama pull gemma3n:e4b-it-q4_K_M

# 3. Install dependencies
poetry install

# 4. Run migrations
alembic upgrade head

# 5. Start API
uvicorn src.api.main:app --reload

# 6. Start UI
streamlit run src/ui/app.py
