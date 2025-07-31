# Documentation API - DHIS2 Blood Bank Service

Cette documentation décrit l'API RESTful du service d'intégration DHIS2 pour le système de gestion des banques de sang.

## 📋 Vue d'ensemble

- **URL de base** : `https://dhis2-service.railway.app/api/v1`
- **Version** : 1.0.0
- **Format** : JSON
- **Authentification** : JWT Token (optionnel pour certains endpoints)

## 🔗 Endpoints Principaux

### Health Checks

#### `GET /health` - Health Check Complet

Vérifie l'état général du service, incluant la connectivité base de données et DHIS2.

**Réponse** :
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "database_status": "healthy",
  "dhis2_status": "healthy",
  "uptime_seconds": 3600.5
}
```

**Codes de statut** :
- `200` : Service sain
- `503` : Service dégradé

#### `GET /health/live` - Liveness Probe

Probe de vivacité pour Kubernetes/Docker.

**Réponse** :
```json
{
  "status": "alive",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### `GET /health/ready` - Readiness Probe

Probe de disponibilité pour vérifier si le service peut traiter les requêtes.

**Réponse** :
```json
{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### `GET /health/metrics` - Métriques Système

Métriques pour monitoring et dashboards.

**Réponse** :
```json
{
  "total_donations": 1250,
  "total_products": 3750,
  "available_products": 2800,
  "expired_products": 45,
  "blood_type_distribution": {
    "A+": 450,
    "A-": 120,
    "B+": 380,
    "B-": 95,
    "AB+": 85,
    "AB-": 25,
    "O+": 520,
    "O-": 145
  },
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### `GET /health/version` - Information de Version

Informations sur la version du service.

**Réponse** :
```json
{
  "service": "DHIS2 Blood Bank Service",
  "version": "1.0.0",
  "api_version": "/api/v1",
  "build_time": "2024-01-15T08:00:00Z"
}
```

### Import de Données

#### `POST /import/donors` - Import de Donneurs

Importe une liste de donneurs dans le système.

**Corps de la requête** :
```json
[
  {
    "id": "DONOR_001",
    "age": 30,
    "gender": "MALE",
    "occupation": "Teacher",
    "location": "Douala",
    "contact_info": "+237123456789"
  },
  {
    "id": "DONOR_002",
    "age": 25,
    "gender": "FEMALE",
    "occupation": "Nurse",
    "location": "Yaounde",
    "contact_info": "+237987654321"
  }
]
```

**Réponse** :
```json
{
  "status": "completed",
  "imported_count": 2,
  "failed_count": 0,
  "errors": [],
  "message": "Successfully imported 2 donors"
}
```

**Validation** :
- `age` : Entre 18 et 65 ans
- `gender` : "MALE", "FEMALE", ou "OTHER"
- `id` : Unique, obligatoire

#### `POST /import/donations` - Import de Donations

Importe des enregistrements de donations.

**Corps de la requête** :
```json
[
  {
    "id": "DONATION_001",
    "donor_id": "DONOR_001",
    "donation_date": "2024-01-15T10:00:00Z",
    "blood_type": "A+",
    "volume_collected": 450.0,
    "collection_site": "Douala General Hospital",
    "staff_id": "STAFF_001"
  }
]
```

**Réponse** :
```json
{
  "status": "completed",
  "imported_count": 1,
  "failed_count": 0,
  "errors": [],
  "message": "Successfully imported 1 donations"
}
```

**Validation** :
- `donor_id` : Doit exister dans la base
- `volume_collected` : Entre 300 et 500 ml
- `blood_type` : Types valides (A+, A-, B+, B-, AB+, AB-, O+, O-)

#### `POST /import/blood-products` - Import de Produits Sanguins

Importe des produits sanguins pour l'inventaire.

**Corps de la requête** :
```json
[
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
]
```

**Réponse** :
```json
{
  "status": "completed",
  "imported_count": 1,
  "failed_count": 0,
  "errors": [],
  "message": "Successfully imported 1 blood products"
}
```

**Statuts de produits** :
- `AVAILABLE` : Disponible
- `RESERVED` : Réservé
- `EXPIRED` : Expiré
- `USED` : Utilisé
- `QUARANTINE` : En quarantaine

#### `POST /import/screening-results` - Import de Résultats de Dépistage

Importe les résultats de tests de dépistage.

**Corps de la requête** :
```json
[
  {
    "donor_id": "DONOR_001",
    "blood_type": "A+",
    "hemoglobin_level": 14.5,
    "hiv_test": true,
    "hepatitis_b_test": true,
    "hepatitis_c_test": true,
    "syphilis_test": true,
    "screening_date": "2024-01-15T09:00:00Z"
  }
]
```

**Réponse** :
```json
{
  "status": "completed",
  "imported_count": 1,
  "failed_count": 0,
  "errors": [],
  "message": "Successfully imported 1 screening results"
}
```

**Validation** :
- `hemoglobin_level` : Entre 12.0 et 20.0 g/dL
- Tests booléens : `true` = négatif (bon), `false` = positif (problème)

### Synchronisation DHIS2

#### `GET /sync/status` - Statut de Synchronisation

Récupère le statut de synchronisation avec DHIS2.

**Réponse** :
```json
{
  "last_sync": "2024-01-15T09:00:00Z",
  "sync_status": "healthy",
  "records_synced": 150,
  "errors": []
}
```

**Statuts possibles** :
- `idle` : Au repos
- `syncing` : Synchronisation en cours
- `healthy` : Dernière sync réussie
- `error` : Erreurs dans la dernière sync

#### `POST /sync/donations` - Synchroniser les Donations

Lance une synchronisation des donations vers DHIS2.

**Paramètres de requête** :
- `days_back` (optionnel) : Nombre de jours à synchroniser (défaut: 7)

**Exemple** :
```
POST /sync/donations?days_back=30
```

**Réponse** :
```json
{
  "status": "started",
  "sync_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Donation sync initiated for last 30 days"
}
```

#### `POST /sync/inventory` - Synchroniser l'Inventaire

Lance une synchronisation de l'inventaire actuel vers DHIS2.

**Réponse** :
```json
{
  "status": "started",
  "sync_id": "550e8400-e29b-41d4-a716-446655440001",
  "message": "Inventory sync initiated"
}
```

#### `POST /sync/full` - Synchronisation Complète

Lance une synchronisation complète (donations + inventaire + donneurs).

**Réponse** :
```json
{
  "status": "started",
  "sync_id": "550e8400-e29b-41d4-a716-446655440002",
  "message": "Full sync initiated"
}
```

#### `GET /sync/logs/{sync_id}` - Détails de Synchronisation

Récupère les détails d'une opération de synchronisation.

**Réponse** :
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "sync_type": "EXPORT_DONATIONS",
  "status": "SUCCESS",
  "records_processed": 100,
  "records_success": 95,
  "records_failed": 5,
  "error_message": null,
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:05:30Z",
  "dhis2_response": "{\"status\": \"SUCCESS\", \"imported\": 95}"
}
```

#### `DELETE /sync/cache` - Vider le Cache de Sync

Vide le cache de synchronisation pour forcer une synchronisation complète.

**Réponse** :
```json
{
  "status": "success",
  "message": "Sync cache cleared"
}
```

## 🔒 Authentification

### JWT Token (Optionnel)

Pour les endpoints nécessitant une authentification :

**Header** :
```
Authorization: Bearer <your-jwt-token>
```

**Obtenir un token** (si implémenté) :
```bash
curl -X POST /auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

### API Key (Alternative)

**Header** :
```
X-API-Key: bbas_your-api-key-here
```

## 📝 Codes d'Erreur

### Codes de Statut HTTP

- `200` : Succès
- `201` : Créé avec succès
- `400` : Requête invalide
- `401` : Non autorisé
- `403` : Interdit
- `404` : Non trouvé
- `422` : Erreur de validation
- `429` : Trop de requêtes
- `500` : Erreur serveur interne
- `503` : Service indisponible

### Format d'Erreur

```json
{
  "error": "Validation error",
  "detail": "Age must be between 18 and 65",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 📊 Rate Limiting

- **Limite générale** : 100 requêtes/minute
- **Health checks** : Illimité
- **Import de données** : 10 requêtes/minute
- **Synchronisation** : 5 requêtes/minute

**Headers de réponse** :
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248600
```

## 🔍 Exemples d'utilisation

### Import Complet de Données

```bash
# 1. Importer les donneurs
curl -X POST "https://api.example.com/api/v1/import/donors" \
  -H "Content-Type: application/json" \
  -d '[{"id": "D001", "age": 30, "gender": "MALE"}]'

# 2. Importer les donations
curl -X POST "https://api.example.com/api/v1/import/donations" \
  -H "Content-Type: application/json" \
  -d '[{"id": "DON001", "donor_id": "D001", "blood_type": "A+", "volume_collected": 450, "donation_date": "2024-01-15T10:00:00Z", "collection_site": "Hospital", "staff_id": "S001"}]'

# 3. Synchroniser avec DHIS2
curl -X POST "https://api.example.com/api/v1/sync/full"
```

### Surveillance de la Synchronisation

```bash
# Démarrer la sync
sync_response=$(curl -X POST "https://api.example.com/api/v1/sync/donations")
sync_id=$(echo $sync_response | jq -r '.sync_id')

# Surveiller le progrès
while true; do
  status=$(curl -s "https://api.example.com/api/v1/sync/logs/$sync_id" | jq -r '.status')
  echo "Status: $status"
  if [[ "$status" == "SUCCESS" || "$status" == "FAILED" ]]; then
    break
  fi
  sleep 10
done
```

### Monitoring de Santé

```bash
#!/bin/bash
# Script de monitoring

URL="https://api.example.com/api/v1"

# Vérifier la santé
health=$(curl -s "$URL/health")
status=$(echo $health | jq -r '.status')

if [[ "$status" != "healthy" ]]; then
  echo "ALERT: Service unhealthy - $status"
  # envoyer alerte
fi

# Vérifier les métriques
metrics=$(curl -s "$URL/health/metrics")
expired=$(echo $metrics | jq -r '.expired_products')

if [[ $expired -gt 10 ]]; then
  echo "WARNING: $expired expired products"
fi
```

## 📚 Documentation Interactive

- **Swagger UI** : https://api.example.com/docs
- **ReDoc** : https://api.example.com/redoc
- **OpenAPI JSON** : https://api.example.com/openapi.json

## 🐛 Troubleshooting

### Erreurs Communes

#### Import échoue avec "Donor not found"
```json
{
  "status": "completed",
  "imported_count": 0,
  "failed_count": 1,
  "errors": ["Donation DON001: Donor D001 not found"]
}
```
**Solution** : Importer d'abord les donneurs avant les donations.

#### Synchronisation DHIS2 échoue
```json
{
  "dhis2_status": "unhealthy: connection failed"
}
```
**Solution** : Vérifier les credentials DHIS2 et la connectivité réseau.

#### Rate limiting activé
```json
{
  "error": "Too Many Requests",
  "detail": "Rate limit exceeded"
}
```
**Solution** : Réduire la fréquence des requêtes ou demander une augmentation de limite.

## 📞 Support

- **Issues** : GitHub Issues
- **Documentation** : `/docs`
- **Email** : piodjiele@gmail.com

---

**Version** : 1.0.0  
