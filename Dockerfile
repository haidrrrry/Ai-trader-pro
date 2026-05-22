FROM node:20-alpine AS frontend
WORKDIR /app/service/frontend
COPY service/frontend/package.json service/frontend/package-lock.json ./
RUN npm ci
COPY service/frontend/ ./
RUN npm run build

FROM python:3.11-slim AS api
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/service/server

COPY service/requirements.txt ./service/requirements.txt
RUN pip install --no-cache-dir -r service/requirements.txt

COPY service/server ./service/server
COPY skills ./skills
COPY docs ./docs
COPY --from=frontend /app/service/frontend/dist ./service/frontend/dist

EXPOSE 8000
CMD ["python", "service/server/main.py"]
