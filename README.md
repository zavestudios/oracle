# oracle

Platform-managed workload deployed via GitOps.

## Local Development

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development without Docker)

### Quick Start

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```

2. Start the application:
   ```bash
   docker-compose up
   ```

3. Application runs at `http://localhost:8000`

### Development Without Docker

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run application:
   ```bash
   python -m oracle.main
   ```

### Testing

```bash
pytest tests/
```

## Deployment

This workload is deployed automatically via GitOps when changes are merged to main.

See `zave.yaml` for workload configuration.
