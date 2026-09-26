# Module: Deployment

## Goal
One command to run the entire stack — required for "plug-and-play for judges".

## Tech stack
**Docker Compose** — containerizes backend + frontend, no manual setup for judges.

## docker-compose.yml
```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./common:/app/common
      - ./database:/app/database
    environment:
      - DATABASE_URL=sqlite:///./altcredit.db
      - BANK_API_KEY=${BANK_API_KEY}
    depends_on:
      - bank_mock

  bank_mock:
    build: ./backend/bank_integration_mock
    ports:
      - "9000:9000"
    environment:
      - BANK_API_KEY=${BANK_API_KEY}

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```
Note: `bank_mock` is the stretch-goal service from `backend/bank_integration_mock/README.md` —
if your team doesn't build it, just delete that service block and the `depends_on` line.

Create a `.env` file at the repo root (already gitignored) with:
```
BANK_API_KEY=some-random-dev-secret
```

## backend/Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## backend/requirements.txt
```
fastapi
uvicorn[standard]
sqlalchemy
pydantic
pandas
scikit-learn
xgboost
shap
weasyprint
jinja2
python-jose[cryptography]
passlib[bcrypt]
python-multipart
```

## frontend/Dockerfile
```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "run", "preview", "--", "--host", "--port", "3000"]
```

## Tasks checklist
- [ ] Write both Dockerfiles
- [ ] Write `docker-compose.yml`
- [ ] Test `docker compose up --build` from a clean clone
- [ ] Document any manual seed step (e.g. `docker compose exec backend python seed_db.py`) in the root README

## Handoff
This is the last step before demo — whoever finishes their module first should own this and do a
full clean-clone test run before the deadline.
