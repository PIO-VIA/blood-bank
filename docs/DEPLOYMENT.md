# Guide de Déploiement - Blood Bank AI System

Ce guide détaille les procédures de déploiement du système d'IA pour la gestion des banques de sang.

## 🏗️ Architecture de Déploiement

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │   ML Service    │    │ Optimization    │
│   (Vercel)      │    │ (HuggingFace)   │    │ (Google Cloud)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  DHIS2 Service  │
                    │   (Railway)     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │  PostgreSQL     │
                    │  (Supabase)     │
                    └─────────────────┘
```

## 🚀 Environnements

### Development (Local)
- **Infrastructure** : Docker Compose
- **Base de données** : PostgreSQL local
- **URLs** : http://localhost:8001

### Staging
- **Infrastructure** : Railway
- **Base de données** : Railway PostgreSQL
- **URL** : https://dhis2-service-staging.up.railway.app
- **Branche** : `develop`

### Production
- **Infrastructure** : Railway
- **Base de données** : Supabase
- **URL** : https://dhis2-service-production.up.railway.app
- **Branche** : `main`

## 📋 Prérequis

### Outils Requis
- Docker et Docker Compose
- Git
- Node.js 18+ (pour les outils de build)
- Railway CLI (pour déploiement manuel)

### Comptes et Services
- Compte GitHub (pour CI/CD)
- Compte Railway (pour hébergement backend)
- Compte Supabase (pour base de données production)
- Compte Vercel (pour frontend)
- Instance DHIS2 (pour intégration)

## 🔧 Configuration

### 1. Variables d'Environnement

#### Développement Local
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Configurer les variables essentielles
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/blood_bank_db
DHIS2_BASE_URL=https://play.dhis2.org/dev
DHIS2_USERNAME=admin
DHIS2_PASSWORD=district
SECRET_KEY=your-local-secret-key
```

#### Staging
```bash
# Railway automatiquement via GitHub Actions
DATABASE_URL=${{ RAILWAY_POSTGRESQL_URL }}
DHIS2_BASE_URL=${{ secrets.STAGING_DHIS2_URL }}
SECRET_KEY=${{ secrets.STAGING_SECRET_KEY }}
```

#### Production
```bash
# Configuration via Railway Dashboard ou CLI
DATABASE_URL=${{ SUPABASE_DATABASE_URL }}
DHIS2_BASE_URL=${{ secrets.PRODUCTION_DHIS2_URL }}
SECRET_KEY=${{ secrets.PRODUCTION_SECRET_KEY }}
```

### 2. Secrets GitHub

Configurer les secrets suivants dans GitHub :

```bash
# Railway
RAILWAY_TOKEN=your-railway-token

# URLs de déploiement
STAGING_DHIS2_URL=https://your-staging-url.railway.app
PRODUCTION_DHIS2_URL=https://your-production-url.railway.app

# DHIS2
STAGING_DHIS2_USERNAME=staging-username
STAGING_DHIS2_PASSWORD=staging-password
PRODUCTION_DHIS2_USERNAME=production-username
PRODUCTION_DHIS2_PASSWORD=production-password

# Clés de sécurité
STAGING_SECRET_KEY=staging-secret-key
PRODUCTION_SECRET_KEY=production-secret-key

# Notifications
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

## 🐳 Déploiement Local

### Démarrage Rapide

```bash
# Cloner le repository
git clone https://github.com/your-org/blood-bank-ai-system.git
cd blood-bank-ai-system

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos configurations

# Démarrer tous les services
docker-compose up -d

# Vérifier le déploiement
curl http://localhost:8001/api/v1/health
```

### Services Individuels

```bash
# DHIS2 Service seulement
docker-compose up -d dhis2-service postgres redis

# Avec monitoring
docker-compose up -d dhis2-service postgres redis prometheus grafana

# Logs en temps réel
docker-compose logs -f dhis2-service
```

## ☁️ Déploiement Cloud

### Railway (Automatique via CI/CD)

Le déploiement sur Railway est automatique via GitHub Actions :

1. **Push vers `develop`** → Déploiement staging
2. **Push vers `main`** → Déploiement production

#### Configuration Railway

```bash
# Installation Railway CLI
npm install -g @railway/cli

# Login
railway login

# Lier le projet
railway link

# Déployer manuellement (si nécessaire)
railway up
```

### Configuration Base de Données

#### Supabase (Production)

```sql
-- Créer la base de données
CREATE DATABASE blood_bank_production;

-- Configurer les extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- URL de connexion à configurer dans Railway
postgresql://user:password@db.supabase.co:5432/blood_bank_production
```

#### Railway PostgreSQL (Staging)

```bash
# La base de données est créée automatiquement
# URL disponible dans les variables d'environnement Railway
DATABASE_URL=${{ RAILWAY_POSTGRESQL_URL }}
```

### Vérification du Déploiement

```bash
# Health check
curl https://your-service-url.railway.app/api/v1/health

# Version
curl https://your-service-url.railway.app/api/v1/health/version

# Documentation API
open https://your-service-url.railway.app/docs
```

## 🔄 Pipeline CI/CD

### Workflow GitHub Actions

Le pipeline automatique inclut :

1. **Tests** : Tests unitaires et d'intégration
2. **Build** : Construction des images Docker
3. **Security** : Scan de sécurité avec Trivy
4. **Deploy** : Déploiement automatique
5. **Verification** : Tests post-déploiement

### Déclencheurs

```yaml
# Déploiement staging
on:
  push:
    branches: [develop]

# Déploiement production
on:
  push:
    branches: [main]
```

### Rollback

```bash
# Via Railway CLI
railway rollback

# Via GitHub (revert commit)
git revert <commit-hash>
git push origin main
```

## 📊 Monitoring et Observabilité

### Métriques

- **Health Checks** : Endpoints automatiques
- **Prometheus** : Métriques application
- **Grafana** : Dashboards visuels
- **Logs** : Logs structurés JSON

### Alertes

Configuration des alertes Slack :

```yaml
# Dans GitHub Actions
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
    status: failure
    text: "Deployment failed"
```

### URLs Monitoring

- **Staging** : https://grafana-staging.railway.app
- **Production** : https://grafana-production.railway.app

## 🔒 Sécurité

### SSL/TLS

- **Railway** : SSL automatique
- **Custom Domain** : Configuration DNS requise

### Secrets Management

- **Development** : Fichier `.env` local
- **Staging/Production** : Variables Railway
- **CI/CD** : GitHub Secrets

### Backup

```bash
# Backup automatique base de données (Supabase)
# Configuration dans le dashboard Supabase

# Backup manuel
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

## 🧪 Tests de Déploiement

### Tests Post-Déploiement

```bash
#!/bin/bash
# Script de validation post-déploiement

URL=$1

echo "Testing deployment at $URL"

# Health check
curl -f "$URL/api/v1/health" || exit 1

# API functionality
curl -f "$URL/api/v1/health/metrics" || exit 1

# Documentation
curl -f "$URL/docs" > /dev/null || exit 1

echo "All tests passed!"
```

### Load Testing

```bash
# Installation d'Apache Bench
sudo apt-get install apache2-utils

# Test de charge
ab -n 1000 -c 10 https://your-service.railway.app/api/v1/health
```

## 🐛 Troubleshooting

### Problèmes Courants

#### 1. Service ne démarre pas

```bash
# Vérifier les logs Railway
railway logs

# Vérifier les variables d'environnement
railway variables

# Vérifier la configuration
railway status
```

#### 2. Erreur de connexion base de données

```bash
# Tester la connexion
psql $DATABASE_URL

# Vérifier les credentials
echo $DATABASE_URL
```

#### 3. Health check échoue

```bash
# Logs détaillés
railway logs --tail 100

# Test local de l'image
docker run -p 8001:8001 dhis2-service:latest
curl http://localhost:8001/api/v1/health
```

### Logs et Debugging

```bash
# Railway logs
railway logs --follow

# Docker logs locaux
docker-compose logs -f dhis2-service

# Logs avec filtre
railway logs | grep ERROR
```

## 📚 Ressources

### Documentation

- [Railway Docs](https://docs.railway.app/)
- [Supabase Docs](https://supabase.com/docs)
- [GitHub Actions](https://docs.github.com/en/actions)

### Support

- **Issues** : GitHub Issues
- **Documentation** : `/docs` folder
- **Monitoring** : Grafana dashboards

### Bonnes Pratiques

1. **Toujours tester localement** avant le déploiement
2. **Utiliser le staging** pour validation
3. **Monitorer les métriques** post-déploiement
4. **Garder les secrets sécurisés**
5. **Documenter les changements**

## 🔄 Maintenance

### Mises à jour

```bash
# Mise à jour des dépendances
pip install -r requirements.txt --upgrade

# Mise à jour des images Docker
docker-compose pull
docker-compose up -d

# Redémarrage des services
railway restart
```

### Backup et Restauration

```bash
# Création backup
pg_dump $DATABASE_URL > backup.sql

# Restauration
psql $DATABASE_URL < backup.sql
```

---

**Note** : Ce guide doit être adapté selon vos environnements spécifiques et vos politiques de sécurité organisationnelles.