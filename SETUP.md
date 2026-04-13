# SecondBrain Production Setup Guide

This guide covers setting up SecondBrain for production deployment using Docker secrets.

## Prerequisites

- Docker and Docker Compose installed
- A MongoDB instance (MongoDB Atlas recommended for production)
- A domain name with SSL certificates (for production)

## Docker Secrets Setup

### 1. Create secrets directory
```bash
mkdir -p secrets
chmod 700 secrets
```

### 2. Generate secret key
```bash
python -c "import secrets; print(secrets.token_hex(32))" > secrets/secret_key.txt
chmod 600 secrets/secret_key.txt
```

### 3. Create MongoDB credentials
```bash
echo "your_mongo_username" > secrets/mongo_username.txt
echo "your_mongo_password" > secrets/mongo_password.txt
chmod 600 secrets/mongo_username.txt
chmod 600 secrets/mongo_password.txt
```

### 4. Create .env.production file
```bash
cp .env.production .env
# Edit .env with your actual MongoDB URI and other production values
```

## SSL Certificates

### Self-signed (for testing)
```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem \
  -out ssl/fullchain.pem \
  -subj "/CN=localhost"
```

### Let's Encrypt (for production)
```bash
# Use certbot to generate certificates
sudo certbot certonly --standalone -d yourdomain.com
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/
```

## Nginx Configuration

Create `nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8002;
    }

    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

## Deploy

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down

# Stop and remove volumes
docker-compose -f docker-compose.prod.yml down -v
```

## Health Checks

After deployment, verify health:
```bash
curl http://localhost/status
```

Expected response:
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "chromadb": "connected",
  "ollama": "connected"
}
```

## Monitoring

View logs for each service:
```bash
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs mongodb
docker-compose -f docker-compose.prod.yml logs nginx
```

## Backup

Backup MongoDB data:
```bash
docker exec secondbrain-mongodb mongodump --archive=/data/db/backup.archive
docker cp secondbrain-mongodb:/data/db/backup.archive ./backup_$(date +%Y%m%d).archive
```

Backup ChromaDB:
```bash
tar -czf chromadb_backup_$(date +%Y%m%d).tar.gz ./data/chromadb
```

## Scaling

To scale the backend:
```bash
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

Note: Ensure your load balancer is configured to handle multiple backend instances.
