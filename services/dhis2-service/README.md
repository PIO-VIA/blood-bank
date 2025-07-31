# DHIS2 Blood Bank Service

Service d'intégration DHIS2 pour le système de gestion des banques de sang. Ce service FastAPI gère l'import/export de données, la synchronisation avec DHIS2, et fournit des APIs RESTful pour la gestion des données de banque de sang.

## 🏗️ Architecture

```
┌─────────────────┐
│   FastAPI App   │
│   (Port 8001)   │
└─────────────────┘
         │
    ┌────┼────┐
    │         │
┌───▼───┐ ┌──▼──┐
│ DHIS2 │ │ DB  │
│       │ │     │
└───────┘ └─────┘
```

## 🚀 Démarrage Rapide

### Avec Docker

```bash
# Build et run
docker build -t dhis2-service .
docker run -p 8001:8001 dhis2-service
```

### Développement Local

```bash
# Installation des dépendances
pip install -r requirements.txt

# Variables d'environnement
cp .env.example .env

# Lancer le service
uvicorn app.main:app --reload --port 8001
```

## 📋 Endpoints API

### Health Checks
- `GET /api/v1/health` - Health check complet
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/metrics` - Métriques système

### Import de Données
- `POST /api/v1/import/donors` - Import des donneurs
- `POST /api/v1/import/donations` - Import des donations
- `POST /api/v1/import/blood-products` - Import des produits sanguins
- `POST /api/v1/import/screening-results` - Import des résultats de dépistage

### Synchronisation DHIS2
- `GET /api/v1/sync/status` - Statut de synchronisation
- `POST /api/v1/sync/donations` - Sync donations vers DHIS2
- `POST /api/v1/sync/inventory` - Sync inventaire vers DHIS2
- `POST /api/v1/sync/full` - Synchronisation complète
- `GET /api/v1/sync/logs/{sync_id}` - Détails d'une sync

## 🔧 Configuration

### Variables d'Environnement

```bash
# Application
APP_NAME="DHIS2 Blood Bank Service"
DEBUG=false
SECRET_KEY=your-secret-key

# Base de données
DATABASE_URL=postgresql+asyncpg://user:password@host:port/db

# DHIS2
DHIS2_BASE_URL=https://your-dhis2-instance.org
DHIS2_USERNAME=your-username
DHIS2_PASSWORD=your-password
DHIS2_API_VERSION=40

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=8002
```

### Configuration DHIS2

Le service nécessite la configuration des mappings DHIS2 dans votre fichier `.env` :

```bash
# Unités d'organisation
DHIS2_ORG_UNIT_BLOOD_BANK=YOUR_BLOOD_BANK_ORG_UNIT_ID

# Éléments de données
DHIS2_DE_BLOOD_TYPE=YOUR_BLOOD_TYPE_DATA_ELEMENT_ID
DHIS2_DE_VOLUME_COLLECTED=YOUR_VOLUME_DATA_ELEMENT_ID

# Types d'entités suivies
DHIS2_TET_DONOR=YOUR_DONOR_TRACKED_ENTITY_TYPE_ID
```

## 📊 Modèles de Données

### Donneur (Donor)
```python
{
    "id": "DONOR_001",
    "age": 30,
    "gender": "MALE",
    "occupation": "Teacher",
    "location": "Douala",
    "contact_info": "+237123456789"
}
```

### Donation
```python
{
    "id": "DONATION_001",
    "donor_id": "DONOR_001",
    "donation_date": "2024-01-15T10:00:00Z",
    "blood_type": "A+",
    "volume_collected": 450.0,
    "collection_site": "Douala General Hospital",
    "staff_id": "STAFF_001"
}
```

### Produit Sanguin
```python
{
    "id": "PRODUCT_001",
    "donation_id": "DONATION_001",
    "blood_type": "A+",
    "product_type": "Whole Blood",
    "volume": 450.0,
    "collection_date": "2024-01-15T10:00:00Z",
    "expiry_date": "2024-02-15T10:00:00Z",
    "status": "AVAILABLE",
    "location": "Fridge_A_01",
    "temperature": 4.0
}
```

## 🧪 Tests

### Lancer les Tests

```bash
# Tests unitaires
pytest tests/ -v

# Tests avec couverture
pytest tests/ --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_health.py -v
pytest tests/test_import.py -v
pytest tests/test_sync.py -v
```

### Structure des Tests

```
tests/
├── conftest.py          # Configuration des fixtures
├── test_health.py       # Tests health checks
├── test_import.py       # Tests import de données
├── test_sync.py         # Tests synchronisation
└── fixtures/            # Données de test
```

## 📈 Monitoring

### Métriques Prometheus

Le service expose des métriques sur `/metrics` :

- `http_requests_total` - Nombre total de requêtes HTTP
- `http_request_duration_seconds` - Durée des requêtes HTTP
- `dhis2_sync_total` - Nombre total de synchronisations DHIS2
- `blood_products_total` - Nombre de produits sanguins par type
- `api_errors_total` - Nombre total d'erreurs API

### Logs Structurés

Les logs sont au format JSON avec les champs :
- `timestamp` - Horodatage
- `level` - Niveau de log
- `message` - Message
- `context` - Contexte additionnel

## 🔒 Sécurité

### Authentification

Le service supporte :
- JWT tokens pour l'authentification
- API keys pour l'accès programmatique
- Rate limiting par IP/utilisateur

### Validation des Données

- Validation Pydantic stricte
- Sanitisation des entrées
- Vérification des contraintes métier

### Headers de Sécurité

Headers ajoutés automatiquement :
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security`

## 🐛 Dépannage

### Problèmes Courants

1. **Erreur de connexion DHIS2**
   - Vérifier les credentials dans `.env`
   - Tester la connectivité : `curl -u user:pass https://dhis2-url/api/me`

2. **Erreur de base de données**
   - Vérifier `DATABASE_URL`
   - Vérifier que PostgreSQL est accessible

3. **Import échoue**
   - Vérifier le format des données
   - Consulter les logs pour les détails d'erreur

### Debug Mode

```bash
# Activer le mode debug
DEBUG=true uvicorn app.main:app --reload

# Logs détaillés
LOG_LEVEL=DEBUG uvicorn app.main:app
```

## 📝 Exemples d'Utilisation

### Import de Donneurs

```bash
curl -X POST "http://localhost:8001/api/v1/import/donors" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "DONOR_001",
      "age": 30,
      "gender": "MALE",
      "occupation": "Teacher"
    }
  ]'
```

### Synchronisation avec DHIS2

```bash
# Synchroniser les donations des 7 derniers jours
curl -X POST "http://localhost:8001/api/v1/sync/donations?days_back=7"

# Vérifier le statut
curl "http://localhost:8001/api/v1/sync/status"
```

### Health Check

```bash
curl "http://localhost:8001/api/v1/health"
```

## 🚀 Déploiement

### Docker

```dockerfile
# Dockerfile déjà configuré
docker build -t dhis2-service .
docker run -p 8001:8001 --env-file .env dhis2-service
```

### Railway

```bash
# Déploiement automatique via GitHub
git push origin main
```

### Health Checks

Le service inclut des health checks pour :
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Monitoring systems

## 📚 Documentation API

- **Swagger UI** : http://localhost:8001/docs
- **ReDoc** : http://localhost:8001/redoc
- **OpenAPI JSON** : http://localhost:8001/openapi.json

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changes (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Distribué sous licence MIT. Voir `LICENSE` pour plus d'informations.