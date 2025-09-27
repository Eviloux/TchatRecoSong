# TchatRecoSong

Collecte et modération collaborative de recommandations musicales issues du tchat
Twitch.

## Lecture des commandes Twitch

Twitch interdit d'envoyer des liens cliquables directement dans le tchat. Le bot
`!reco` doit donc se contenter d'afficher l'URL publique de la page "utilisateur"
hébergée par ce dépôt (ex. `https://tchatrecosong-front.onrender.com`). Les viewers y collent
leur lien YouTube ou Spotify ; le backend va chercher les métadonnées
correspondantes via `POST /public/submissions/` et enregistre la recommandation
en base. Les écrans d'administration (liste des chansons, règles de
bannissement) restent réservés aux comptes Google/Twitch autorisés.

## Base de données Neon

Le backend FastAPI est désormais prêt à se connecter à l'instance Neon fournie par défaut. Si aucune variable d'environnement `DATABASE_URL` n'est définie, la connexion utilisera automatiquement l'URL suivante :

```
postgresql://neondb_owner:npg_ljrtUWJ9o7Cs@ep-plain-leaf-ag9ynkn2-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

Pour initialiser les tables (`songs`, `ban_rules`) directement dans Neon, importez le fichier SQL `backend/app/database/neon_schema.sql` via l'outil SQL du tableau de bord Neon ou avec `psql`.

## Configuration authentification & frontend

Le dépôt embarque un fichier `.env` prêt à être copié/collé dans l'interface
"Environment" de Render. Chaque variable y est commentée pour expliquer
précisément la valeur attendue. Voici un rappel synthétique :

| Variable | À renseigner avec... |
| --- | --- |
| `DATABASE_URL` | L'URL PostgreSQL fournie par Render (ou Neon) pour la base de données. |
| `CORS_ORIGINS` | Les domaines autorisés à appeler l'API, séparés par des virgules. |
| `ADMIN_JWT_SECRET` | Une chaîne secrète longue et aléatoire pour signer les JWT admin. |
| `ADMIN_TOKEN_TTL_MINUTES` | Durée de validité des tokens admin (720 = 12 h). |
| `GOOGLE_CLIENT_ID` | L'identifiant OAuth Google obtenu dans Google Cloud Console. |
| `TWITCH_CLIENT_ID` | L'identifiant OAuth Twitch associé à votre application. |
| `ALLOWED_GOOGLE_EMAILS` | Les emails Google autorisés à accéder à l'administration. |
| `ALLOWED_TWITCH_LOGINS` | Les logins Twitch autorisés à accéder à l'administration. |
| `VITE_API_URL` | L'URL publique du backend (ex : `https://tchat-reco-backend.onrender.com`). |
| `VITE_GOOGLE_CLIENT_ID` | Identique à `GOOGLE_CLIENT_ID` pour initialiser le bouton côté front. |
| `VITE_TWITCH_CLIENT_ID` | Identique à `TWITCH_CLIENT_ID` pour l'auth Twitch côté front. |
| `VITE_PUBLIC_VIEWER_URL` | L'URL à afficher dans le tchat Twitch (page publique de soumission). |

### URLs frontend prêtes à l'emploi

- Portail public (viewers) : `https://tchatrecosong-front.onrender.com/`
- Page de connexion administrateur : `https://tchatrecosong-front.onrender.com/admin`
- Tableau de bord administrateur (après authentification) : `https://tchatrecosong-front.onrender.com/admin`

> ℹ️ Le tableau de bord admin demande une authentification Google ou Twitch. Assure-toi
> que l'adresse ou le login de chaque membre de l'équipe figure bien dans
> `ALLOWED_GOOGLE_EMAILS` ou `ALLOWED_TWITCH_LOGINS`.

> 💡 Les jetons générés par `POST /auth/google` et `POST /auth/twitch` sont valables
> `ADMIN_TOKEN_TTL_MINUTES` minutes (12 h par défaut). Ajustez cette valeur si besoin.

### Générer les identifiants et secrets OAuth

Impossible de te fournir des jetons ou des clients OAuth déjà valides — ces valeurs
doivent rester secrètes et spécifiques à ton compte. Voici comment les créer :

1. **Identifiants Google (`GOOGLE_CLIENT_ID` / `VITE_GOOGLE_CLIENT_ID`)**
   - Ouvre [console.cloud.google.com](https://console.cloud.google.com/).
   - Crée un projet (ou utilise-en un existant) puis active l'API "Google Identity Services".
   - Dans "Identifiants", crée un "ID client OAuth 2.0" de type Application Web.
   - Ajoute comme origines autorisées l'URL de ton frontend (Render) et `http://localhost:5173` pour les tests.
   - Copie l'ID client (pas besoin de secret côté frontend) et reporte-le dans `.env`.

2. **Identifiants Twitch (`TWITCH_CLIENT_ID` / `VITE_TWITCH_CLIENT_ID`)**
   - Va sur [dev.twitch.tv/console](https://dev.twitch.tv/console/apps).
   - Crée une application, choisis "Web" comme type et renseigne l'URL de redirection `https://tchatrecosong-front.onrender.com/auth/twitch/callback` (et `http://localhost:5173/auth/twitch/callback` pour le local).
   - Une fois l'appli créée, récupère le `Client ID` (renseigne-le côté backend et frontend) et garde le `Client Secret` dans la console Twitch : il n'est pas nécessaire dans la configuration actuelle qui se contente de valider des tokens d'accès existants.

3. **APIs YouTube & Spotify**
   - Le projet s'appuie sur les endpoints publics oEmbed de YouTube et Spotify, qui ne nécessitent ni clé API ni jeton d'accès supplémentaires.
   - Aucun champ `.env` n'est donc à renseigner pour ces services. Si tu souhaites étendre les fonctionnalités (ex : recherche), crée des clés via la Google Cloud Console ou le Dashboard Spotify Developer et ajuste le code en conséquence.
