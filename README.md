# TchatRecoSong

Collecte et moderation collaborative de recommandations musicales issues du tchat Twitch.

Les viewers soumettent un lien YouTube ou Spotify via un portail public ; le backend extrait automatiquement les metadonnees (titre, artiste, miniature) et enregistre la recommandation. Les administrateurs gerent la liste depuis un tableau de bord protege par authentification Google ou mot de passe.

---

## Fonctionnalites

### Pour les viewers (public)

- **Soumettre une chanson** : coller un lien YouTube ou Spotify sur la page `/submit`. Les metadonnees sont extraites automatiquement via les APIs oEmbed publiques.
- **Ajouter un commentaire** : champ optionnel pour accompagner la recommandation.
- **Voter** : chaque visiteur peut voter une fois par chanson (suivi par navigateur via `localStorage`). Les chansons sont classees par nombre de votes.

### Pour les administrateurs

- **Connexion securisee** : via Google OAuth ou identifiants email/mot de passe.
- **Gerer les chansons** : consulter la liste triee par votes, supprimer une recommandation.
- **Regles de bannissement** : bloquer des chansons par titre, artiste ou lien. Les regles s'appliquent retroactivement (les chansons correspondantes sont supprimees immediatement).

### Anti-abus

- **Rate limiting** : 10 soumissions par minute par adresse IP.
- **Detection de doublons** : par lien exact puis par titre+artiste normalises (insensible a la casse et aux accents).
- **Validation des liens** : seuls YouTube et Spotify sont acceptes cote public ; seules les URLs `http(s)` sont acceptees cote admin.

---

## Architecture

```
TchatRecoSong/
|-- backend/               API FastAPI + PostgreSQL
|   |-- app/
|   |   |-- main.py         Point d'entree, middlewares, routes statiques
|   |   |-- config.py       Variables d'environnement et valeurs par defaut
|   |   |-- api/routes/     Endpoints (songs, ban_rules, public_submissions, auth)
|   |   |-- models/         Modeles SQLAlchemy (Song, BanRule, AdminUser)
|   |   |-- schemas/        Schemas Pydantic (validation entree/sortie)
|   |   |-- crud/           Operations base de donnees
|   |   |-- services/       Logique metier (auth, extraction metadonnees)
|   |   |-- database/       Connexion PostgreSQL
|   |   |-- utils/          Hachage mots de passe, normalisation texte
|   |-- tests/              Tests Pytest
|   |-- requirements.txt
|
|-- frontend/              SPA Vue 3 + TypeScript + Vite
|   |-- src/
|   |   |-- views/          HomeView, LoginView, AdminView
|   |   |-- components/     SongList, AdminPanel
|   |   |-- utils/          api.ts, adminSession.ts
|   |   |-- assets/styles/  SCSS (variables, mixins, composants)
|   |-- server.js           Serveur de production (SPA fallback)
|   |-- vite.config.js
|
|-- render.yaml            Configuration de deploiement Render
```

---

## Endpoints API

### Public

| Methode | Chemin | Description |
|---------|--------|-------------|
| `GET` | `/health` | Verification de disponibilite |
| `GET` | `/songs/` | Liste des chansons (triees par votes desc.) |
| `POST` | `/songs/{id}/vote` | Voter pour une chanson |
| `POST` | `/public/submissions/` | Soumettre un lien (rate limit: 10/min/IP) |
| `GET` | `/ban/` | Liste des regles de bannissement |
| `GET` | `/auth/config` | Configuration des providers d'authentification |

### Admin (JWT requis)

| Methode | Chemin | Description |
|---------|--------|-------------|
| `POST` | `/songs/` | Creer une chanson manuellement |
| `DELETE` | `/songs/{id}` | Supprimer une chanson |
| `POST` | `/ban/` | Creer une regle de bannissement |
| `PUT` | `/ban/{id}` | Modifier une regle |
| `DELETE` | `/ban/{id}` | Supprimer une regle |

### Authentification

| Methode | Chemin | Description |
|---------|--------|-------------|
| `POST` | `/auth/google` | Connexion via token Google |
| `POST` | `/auth/login` | Connexion email/mot de passe |
| `GET` | `/auth/session` | Valider la session courante (JWT requis) |

---

## Modele de donnees

### songs

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer, PK | Identifiant unique |
| `title` | String, indexe | Titre de la chanson |
| `artist` | String, indexe | Nom de l'artiste |
| `link` | String, unique, indexe | URL YouTube ou Spotify |
| `thumbnail` | String, nullable | URL de la miniature |
| `comment` | String, nullable | Commentaire du viewer |
| `votes` | Integer, defaut 1 | Nombre de votes |

### ban_rules

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer, PK | Identifiant unique |
| `title` | String, nullable | Titre a bloquer (correspondance partielle) |
| `artist` | String, nullable | Artiste a bloquer (correspondance partielle) |
| `link` | String, nullable | Lien exact a bloquer |

### admin_users

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer, PK | Identifiant unique |
| `email` | String, unique | Adresse email |
| `password_hash` | String | Hash PBKDF2-SHA256 |
| `display_name` | String, nullable | Nom affiche |
| `is_active` | Boolean, defaut true | Compte actif |
| `created_at` | DateTime | Date de creation |
| `updated_at` | DateTime | Derniere modification |

---

## Synthese technique

### Stack

| Couche | Technologies |
|--------|-------------|
| **Frontend** | Vue 3 (Composition API), TypeScript, Vue Router, Vite, SCSS |
| **Backend** | FastAPI, SQLAlchemy, Pydantic, PyJWT, httpx, slowapi |
| **Base de donnees** | PostgreSQL (Neon ou Render Postgres) |
| **Deploiement** | Render (2 services web : backend Python + frontend Node) |

### Extraction de metadonnees

Quand un viewer soumet un lien, le backend recupere automatiquement le titre, l'artiste et la miniature :

- **YouTube** : appel a l'API oEmbed publique (`youtube.com/oembed`). Le titre et l'artiste (`author_name`) sont directement dans la reponse JSON.
- **Spotify** : appel oEmbed puis, si l'artiste est absent de la reponse, scraping HTML de la page Spotify. Des patterns regex extraient le nom de l'artiste et le titre depuis les donnees JSON embarquees dans le HTML.

Aucune cle API n'est necessaire : les deux providers exposent des endpoints oEmbed publics.

### Detection de doublons

Deux niveaux de verification avant d'inserer une chanson :

1. **Correspondance par lien** : recherche exacte en base sur l'URL. Rapide grace a l'index unique.
2. **Correspondance par titre + artiste** : si le lien est nouveau, le backend compare les valeurs normalisees. La normalisation (`utils/text.py`) decompose les caracteres Unicode (NFKD), supprime les accents, passe en minuscules et retire les caracteres non alphanumeriques. Ainsi `"Cafe au Lait"` et `"cafe au lait!"` correspondent.

Si un doublon est detecte, le compteur de votes est incremente au lieu de creer un nouvel enregistrement.

### Authentification

Deux modes de connexion admin, configurables par variables d'environnement :

- **Google OAuth** : le frontend charge Google Identity Services, envoie le credential token au backend. Celui-ci verifie la signature JWT via les cles publiques Google (JWKS avec cache TTL), valide l'audience et l'emetteur, puis verifie l'email contre la whitelist `ALLOWED_GOOGLE_EMAILS`.
- **Email / mot de passe** : lookup en base, verification du hash PBKDF2-SHA256 (600 000 iterations) avec comparaison a temps constant (`hmac.compare_digest`).

Dans les deux cas, un JWT interne est emis (algorithme HS256, signe avec `ADMIN_JWT_SECRET`, expire apres `ADMIN_TOKEN_TTL_MINUTES` minutes). Le frontend stocke ce token en `localStorage` et l'envoie via le header `Authorization: Bearer`.

### Securite

| Mesure | Detail |
|--------|--------|
| **Rate limiting** | 10 soumissions/min par IP via `slowapi` sur `POST /public/submissions/` |
| **Validation des entrees** | `max_length` Pydantic sur tous les champs string (titre: 500, artiste: 500, lien: 2000, commentaire: 1000) |
| **CORS** | Origines explicites, methodes restreintes (`GET`, `POST`, `DELETE`, `OPTIONS`), headers limites (`Content-Type`, `Authorization`) |
| **Headers HTTP** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` sur backend et frontend |
| **Hachage mots de passe** | PBKDF2-SHA256, 600 000 iterations, sel aleatoire 16 octets |
| **Validation des liens** | Regex YouTube/Spotify sur la route publique ; `http(s)://` obligatoire sur la route admin |
| **Protection anti-timing** | `hmac.compare_digest()` pour la verification des mots de passe |

### Systeme de bannissement

Les regles de bannissement fonctionnent sur trois criteres (au moins un requis) :

- **Par lien** : correspondance exacte sur l'URL.
- **Par titre / artiste** : correspondance partielle sur les valeurs normalisees. La regle `"Beatles"` bloquera `"The Beatles"` car le terme normalise est present comme sous-chaine.

A la creation ou modification d'une regle, le backend l'applique immediatement aux chansons existantes : les correspondances sont supprimees de la base. Les futures soumissions sont egalement verifiees avant insertion.

### Session admin (frontend)

Le token JWT et le profil utilisateur sont persistes dans `localStorage`. Un cache memoire evite les lectures repetees. La validation se fait via `GET /auth/session`. Le router Vue protege la route `/admin` avec un guard de navigation qui redirige vers `/login` si la session est absente ou invalide.

### Resolution automatique de l'URL API

Le frontend (`utils/api.ts`) determine l'URL du backend selon le contexte :

1. Variable `VITE_API_URL` si definie
2. `http://localhost:8000` si le frontend tourne en local
3. Deduction automatique sur Render : remplacement de `-front` dans le hostname (ex: `tchatrecosong-front.onrender.com` -> `tchatrecosong.onrender.com`)

### Serveur frontend de production

Le fichier `server.js` est un serveur HTTP Node.js sans dependance externe qui :
- Sert les fichiers statiques du build Vite (`dist/`)
- Redirige toutes les routes sans extension vers `index.html` (SPA fallback)
- Protege contre le path traversal
- Ajoute les headers de securite sur chaque reponse

---

## Variables d'environnement

### Backend

| Variable | Defaut | Description |
|----------|--------|-------------|
| `DATABASE_URL` | *(requis)* | URL PostgreSQL complete |
| `CORS_ORIGINS` | `https://tchatrecosong-front.onrender.com,http://localhost:5173` | Origines CORS autorisees (separees par virgule) |
| `ADMIN_JWT_SECRET` | *(warning si absent)* | Secret de signature JWT. **A definir en production.** |
| `ADMIN_TOKEN_TTL_MINUTES` | `720` | Duree de validite des tokens admin (12h) |
| `GOOGLE_CLIENT_ID` | *(optionnel)* | ID client OAuth Google |
| `ALLOWED_GOOGLE_EMAILS` | *(vide = tous autorises)* | Emails Google autorises (separes par virgule) |
| `ADMIN_PASSWORD_LOGIN_ENABLED` | `true` | Activer la connexion par mot de passe |
| `ADMIN_DEFAULT_EMAIL` | `admin@tchatrecosong.local` | Email de l'admin par defaut |
| `ADMIN_DEFAULT_PASSWORD` | `recoadmin` | Mot de passe par defaut (si aucun hash fourni) |
| `FRONTEND_DIST_PATH` | `../frontend/dist` | Chemin vers le build frontend |
| `FRONTEND_SUBMIT_REDIRECT_URL` | *(optionnel)* | URL de redirection si le build frontend est absent |

### Frontend

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | URL du backend (ex: `https://tchatrecosong.onrender.com`) |
| `VITE_GOOGLE_CLIENT_ID` | ID client Google (meme valeur que `GOOGLE_CLIENT_ID` cote backend) |

---

## Installation locale

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Editer .env avec DATABASE_URL, ADMIN_JWT_SECRET, etc.

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

cp .env.example .env
# Editer .env avec VITE_API_URL=http://localhost:8000

npm run dev
```

Le frontend sera accessible sur `http://localhost:5173`.

---

## Deploiement sur Render

Le fichier `render.yaml` definit deux services :

| Service | Type | Plan | Description |
|---------|------|------|-------------|
| **TchatRecoSong** | Web (Python) | Free | Backend FastAPI (`uvicorn app.main:app`) |
| **TchatRecoSong-front** | Web (Node) | Free | Frontend Vue (`node server.js`) |

### Configuration des variables sur Render

**Backend** (onglet Environment du service Python) :
- `DATABASE_URL` : URL PostgreSQL (Neon ou Render Postgres)
- `ADMIN_JWT_SECRET` : generer avec `openssl rand -base64 32`
- `GOOGLE_CLIENT_ID` : depuis Google Cloud Console
- `ALLOWED_GOOGLE_EMAILS` : emails autorises
- `CORS_ORIGINS` : URL du frontend

**Frontend** (onglet Environment du service Node) :
- `VITE_API_URL` : URL du backend
- `VITE_GOOGLE_CLIENT_ID` : meme valeur que `GOOGLE_CLIENT_ID`

### Points d'attention

- **`ADMIN_JWT_SECRET`** : obligatoire en production. Sans lui, un secret par defaut public est utilise.
- **`DATABASE_URL` avec Neon** : supprimer le suffixe `&channel_binding=require` de l'URL (incompatible avec psycopg2). Garder uniquement `?sslmode=require`.
- **Free tier Render** : le backend s'endort apres 15 min d'inactivite. Le frontend affiche un message d'attente et poll `/health` toutes les 5 secondes jusqu'au reveil.
- **CORS** : la valeur par defaut couvre `tchatrecosong-front.onrender.com`. Si le frontend a un autre nom, mettre a jour `CORS_ORIGINS`.

### URLs en production

| Page | URL |
|------|-----|
| Portail public (viewers) | `https://tchatrecosong-front.onrender.com/submit` |
| Connexion admin | `https://tchatrecosong-front.onrender.com/login` |
| Tableau de bord admin | `https://tchatrecosong-front.onrender.com/admin` |

---

## Tests

```bash
cd backend
pytest
```

Les tests couvrent : health check, configuration auth, authentification par mot de passe, validation de session, gestion des chansons, extraction de metadonnees et flux de soumission publique.
