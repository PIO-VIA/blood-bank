# Blood Bank AI System - DHIS2 Integration Service

[![CI/CD Pipeline](https://github.com/your-org/blood-bank-ai-system/workflows/CI/CD%20Pipeline%20-%20Blood%20Bank%20AI%20System/badge.svg)](https://github.com/your-org/blood-bank-ai-system/actions)
[![Coverage](https://codecov.io/gh/your-org/blood-bank-ai-system/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/blood-bank-ai-system)

Système d'intelligence artificielle pour la gestion des banques de sang avec intégration DHIS2, développé pour l'Hôpital Général de Douala.

## 🏗️ Architecture du Système

Le système est composé de 5 microservices principaux :

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │    │   ML Service    │    │ Optimization    │
│   (React)       │    │   (TensorFlow)  │    │ Service (PuLP)  │
│   Port: 3000    │    │   Port: 8002    │    │   Port: 8003    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  DHIS2 Service  │
                    │   (FastAPI)     │
                    │   Port: 8001    │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │  PostgreSQL     │
                    │   (Supabase)    │
                    │   Port: 5432    │
                    └─────────────────┘
```

## 🚀 Démarrage Rapide

### Prérequis

- Docker et Docker Compose
- Python 3.11+
- Node.js 18+ (pour le dashboard)
- PostgreSQL 15+

### Installation

1. **Cloner le repository**
```bash
git clone https://github.com/Nathech23/High-Five.git
cd blood-bank-ai-system
```

2. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

3. **Lancer les services avec Docker Compose**
```bash
docker-compose up -d
```

4. **Vérifier le déploiement**
```bash
# Health check du service DHIS2
curl http://localhost:8001/api/v1/health

# Vérifier les logs
docker-compose logs -f dhis2-service
```

## 📋 Services et Endpoints

### Service DHIS2 (Port 8001)
Responsable de l'intégration avec DHIS2 et de la gestion des données de base.

#### Endpoints Principaux
- `GET /api/v1/health` - Health check complet
- `POST /api/v1/import/donors` - Import des données de donneurs
- `POST /api/v1/import/donations` - Import des donations
- `POST /api/v1/import/blood-products` - Import des produits sanguins
- `POST /api/v1/sync/donations` - Synchronisation avec DHIS2
- `GET /api/v1/sync/status` - Status de synchronisation

#### Documentation API
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### Base de Données

Le système utilise PostgreSQL avec les tables principales :
- `donors` - Informations des donneurs
- `donations` - Enregistrements de donations
- `blood_products` - Inventaire des produits sanguins
- `screening_results` - Résultats de dépistage
- `sync_logs` - Logs de synchronisation DHIS2

## 🔧 Configuration

### Variables d'Environnement Essentielles

```bash
# Base de données
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/blood_bank_db

# DHIS2
DHIS2_BASE_URL=https://your-dhis2-instance.org
DHIS2_USERNAME=your-username
DHIS2_PASSWORD=your-password

# Sécurité
SECRET_KEY=your-secret-key-here

# Monitoring
ENABLE_METRICS=true
```

### Configuration DHIS2

Le service nécessite la configuration des éléments suivants dans DHIS2 :

1. **Unités d'Organisation**
   - Banque de sang principale
   - Sites de collecte

2. **Éléments de Données**
   - Type sanguin
   - Volume collecté
   - Données démographiques des donneurs

3. **Types d'Entités Suivies**
   - Type d'entité pour les donneurs

## 🧪 Tests

### Lancer les Tests

```bash
# Tests unitaires
cd services/dhis2-service
pytest tests/ -v

# Tests avec couverture
pytest tests/ --cov=app --cov-report=html

# Tests d'intégration
pytest tests/integration/ -v
```

### Structure des Tests

```
tests/
├── conftest.py          # Configuration des fixtures
├── test_health.py       # Tests des endpoints de santé
├── test_import.py       # Tests d'import de données
├── test_sync.py         # Tests de synchronisation
└── integration/         # Tests d'intégration
    └── test_dhis2.py
```

## 📊 Monitoring et Observabilité

### Métriques Prometheus

Le service expose des métriques sur le port 8002 :
- Nombre de requêtes HTTP
- Temps de réponse des APIs
- Statut des synchronisations DHIS2
- Métriques métier (donations, stock)

### Dashboards Grafana

Dashboards disponibles sur http://localhost:3000 :
- Vue d'ensemble du système
- Performance des APIs
- Métriques de synchronisation DHIS2
- Alertes et anomalies

### Logs Structurés

Les logs sont formatés en JSON et incluent :
- Timestamp et niveau de log
- Contexte de la requête
- Métadonnées de traçabilité
- Erreurs détaillées

## 🚀 Déploiement

### Pipeline CI/CD

Le système utilise GitHub Actions pour :
1. Tests automatiques sur chaque PR
2. Build et push des images Docker
3. Déploiement automatique sur Railway
4. Scan de sécurité avec Trivy

### Environnements

- **Development** : Docker Compose local
- **Staging** : Railway (branche develop)
- **Production** : Railway (branche main)


## 🔒 Sécurité

### Mesures de Sécurité

- Authentification JWT
- Chiffrement des données sensibles
- Rate limiting sur les APIs
- Headers de sécurité HTTP
- Validation stricte des entrées
- Audit trail complet

### Compliance

Le système est conçu pour respecter :
- GDPR (Protection des données)
- HIPAA (Données de santé)
- Standards DHIS2

## 🐛 Dépannage

### Problèmes Courants

1. **Erreur de connexion DHIS2**
```bash
# Vérifier la connectivité
curl -u username:password https://your-dhis2-instance.org/api/me
```

2. **Problème de base de données**
```bash
# Vérifier la connexion PostgreSQL
docker-compose logs postgres
```

3. **Service indisponible**
```bash
# Vérifier les health checks
docker-compose ps
curl http://localhost:8001/api/v1/health
```

### Logs et Debugging

```bash
# Voir tous les logs
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f dhis2-service

# Mode debug
DEBUG=true docker-compose up
```

## 🤝 Contribution

### Guidelines de Développement

1. Créer une branche feature
2. Écrire des tests pour le nouveau code
3. Assurer une couverture de tests > 80%
4. Suivre les conventions de code (Black, isort)
5. Créer une Pull Request

### Structure du Code

```
services/dhis2-service/
├── app/
│   ├── core/           # Configuration et sécurité
│   ├── models/         # Modèles de données
│   ├── routers/        # Endpoints API
│   ├── services/       # Logique métier
│   └── utils/          # Utilitaires
├── tests/              # Tests unitaires
└── Dockerfile         # Configuration Docker
```

## 📈 Roadmap

### Phase 1 - Fondations (Terminé)
- [x] Service DHIS2 avec APIs de base
- [x] Intégration PostgreSQL
- [x] Pipeline CI/CD
- [x] Tests automatiques

### Phase 2 - Intelligence (En cours)
- [ ] Service ML pour prédictions
- [ ] Service d'optimisation
- [ ] Intégration LLM
- [ ] Dashboard React

### Phase 3 - Production (Prochaine)
- [ ] Déploiement production
- [ ] Formation utilisateurs
- [ ] Documentation complète
- [ ] Support et maintenance

## 📞 Support

- **Documentation** : Voir le dossier `/docs`
- **Issues** : GitHub Issues
- **Contact** : piodjiele@gmail.com

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

