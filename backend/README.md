# REST API Template

A production-ready FastAPI template for building scalable REST APIs with Docker support, rate limiting, logging, and security features.

## 🚀 Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Docker Support**: Multi-stage Dockerfile and docker-compose for easy deployment
- **Rate Limiting**: Built-in request rate limiting with SlowAPI
- **Logging**: Comprehensive logging system with file and console output
- **Security**: Non-root user in Docker, input validation, encryption utilities
- **Configuration**: JSON-based configuration management
- **Health Checks**: Built-in health check endpoints
- **Development Ready**: Hot reload support for development

## 📁 Project Structure

```
rest_api_template/
├── src/
│   ├── api_endpoints/          # API route definitions
│   │   ├── routers/           # Additional router modules
│   │   └── root_endpoint.py   # Root/health check endpoint
│   ├── core_specs/            # Core configuration and data
│   │   ├── configuration/     # JSON config files and loaders
│   │   └── data/             # Data files and loaders
│   └── utils/                # Utility modules
│       ├── custom_logger.py  # Logging configuration
│       ├── limiter.py        # Rate limiting setup
│       ├── validators.py     # Input validation utilities
│       ├── en_de_crypt.py    # Encryption/decryption utilities
│       └── request_limiter.py # Rate limit handlers
├── logs/                     # Log files (created automatically)
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── DOCKERFILE               # Docker build configuration
├── docker-compose.yml       # Docker compose configuration
├── .env                     # Environment variables template
├── .dockerignore           # Docker ignore file
└── README.md               # This file
```

## 🛠️ Quick Start

### Option 1: Run with Python (Development)

1. **Clone and setup**:
   ```bash
   cd templates/rest_api_template
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env .env.local
   # Edit .env.local with your configuration
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

4. **Access the API**:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### Option 2: Run with Docker (Production)

1. **Build and run with Docker Compose**:
   ```bash
   cd templates/rest_api_template
   docker-compose up --build
   ```

2. **Or build and run manually**:
   ```bash
   docker build -t rest-api-template .
   docker run -p 8000:8000 --env-file .env rest-api-template
   ```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Server Configuration
SERVER_PORT=8000
HOST=0.0.0.0
RELOAD=false
WORKERS=1

# Security Keys
E_PRIVATE_KEY=your_private_key_here
E_PRIVATE_PASSWORD=your_private_password_here
E_PUBLIC_KEY=your_public_key_here

# Logging
LOG_LEVEL=info
```

### JSON Configuration (src/core_specs/configuration/config_file.json)

The template uses JSON-based configuration for:
- Network settings (host, port, workers)
- Endpoint configurations (rate limits, routes)
- Logging settings
- Email validation rules

## 📝 Adding New Endpoints

1. **Create a new router file** in `src/api_endpoints/routers/`:
   ```python
   from fastapi import APIRouter, Request
   from src.utils.limiter import limiter
   from src.core_specs.configuration.config_loader import config_loader
   
   router = APIRouter(prefix="/api/v1", tags=["your_tag"])
   
   @router.get("/your-endpoint")
   @limiter.limit("10/minute")
   async def your_endpoint(request: Request):
       return {"message": "Your endpoint response"}
   ```

2. **Register the router** in `main.py`:
   ```python
   from src.api_endpoints.routers.your_router import router as your_router
   app.include_router(your_router)
   ```

3. **Update configuration** in `config_file.json` if needed.

## 🔒 Security Features

- **Rate Limiting**: Configurable per-endpoint rate limiting
- **Input Validation**: Pydantic models for request validation
- **Encryption**: Built-in encryption/decryption utilities
- **Non-root Docker**: Container runs as non-root user
- **Environment Variables**: Sensitive data via environment variables

## 📊 Logging

The template includes comprehensive logging:
- **File Logging**: Timestamped log files in `logs/` directory
- **Console Logging**: Structured output for containers
- **Configurable Levels**: Debug, Info, Warning, Error, Critical
- **Request Logging**: Automatic API request logging

## 🐳 Docker Features

### Multi-stage Build
- **Builder stage**: Installs dependencies
- **Production stage**: Minimal runtime image
- **Security**: Non-root user execution
- **Health checks**: Built-in container health monitoring

### Docker Compose
- **Development**: Hot reload support (commented)
- **Production**: Optimized for deployment
- **Services**: Ready for Redis, PostgreSQL integration
- **Volumes**: Persistent log storage

## 🧪 Development

### Hot Reload Development
```bash
# Enable hot reload in docker-compose.yml
docker-compose up --build
```

### Adding Dependencies
```bash
pip install new-package
pip freeze > requirements.txt
```

### Running Tests
```bash
# Add your test framework
pip install pytest
pytest tests/
```

## 🚀 Deployment

### Production Deployment
1. **Update environment variables** for production
2. **Build production image**:
   ```bash
   docker build -t your-api:latest .
   ```
3. **Deploy with docker-compose**:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

### Cloud Deployment
The template is ready for deployment on:
- **AWS ECS/Fargate**
- **Google Cloud Run**
- **Azure Container Instances**
- **Heroku**
- **DigitalOcean App Platform**

## 📚 API Documentation

Once running, access interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Customization

### Changing the API Title/Description
Update in `main.py`:
```python
app = FastAPI(
    title="Your API Name",
    description="Your API Description",
    version="1.0.0"
)
```

### Adding Database Support
1. Uncomment database service in `docker-compose.yml`
2. Add database dependencies to `requirements.txt`
3. Create database connection utilities in `src/utils/`

### Adding Authentication
1. Install authentication dependencies
2. Create auth utilities in `src/utils/`
3. Add authentication middleware to `main.py`

## 📋 Requirements

- Python 3.12+
- Docker (optional)
- Docker Compose (optional)

## 🤝 Contributing

This is a template - customize it for your specific needs:
1. Update configuration files
2. Add your business logic
3. Implement your endpoints
4. Add tests
5. Update documentation

## 📄 License

This template is provided as-is for educational and development purposes.

---

**Ready to build your REST API!** 🚀

Start by customizing the configuration files and adding your endpoints in the `src/api_endpoints/` directory.