# TchatRecoSong

Collecte et modération collaborative de recommandations musicales issues du tchat
Twitch.

## Lecture des commandes Twitch

Twitch interdit d'envoyer des liens cliquables directement dans le tchat. Le bot
`!reco` doit donc se contenter d'afficher l'URL publique de la page "utilisateur"
hébergée par ce dépôt (ex. `https://wizbit.example/reco`). Les viewers y collent
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

Les variables suivantes pilotent les accès administrateur et le portail frontend :

| Variable | Description |
| --- | --- |
| `ADMIN_JWT_SECRET` | Secret HMAC pour signer les jetons admin (obligatoire en production). |
| `ALLOWED_GOOGLE_EMAILS` | Liste (séparée par des virgules) des adresses Google autorisées. |
| `ALLOWED_TWITCH_LOGINS` | Liste des logins Twitch autorisés. |
| `GOOGLE_CLIENT_ID` | Client ID OAuth Google utilisé pour vérifier les `credential`. |
| `TWITCH_CLIENT_ID` | Client ID OAuth Twitch pour valider les tokens. |
| `VITE_API_URL` | URL du backend, consommée par le frontend (ex : `http://localhost:8000`). |
| `VITE_GOOGLE_CLIENT_ID` | Même valeur que côté backend pour initialiser le bouton Google. |
| `VITE_TWITCH_CLIENT_ID` | Identifiant Twitch utilisé pour l'implicit flow côté frontend. |
| `VITE_PUBLIC_VIEWER_URL` | (Optionnel) URL absolue à afficher dans le tchat Twitch ; reprise dans l'interface publique. |

> 💡 Les jetons générés par `POST /auth/google` et `POST /auth/twitch` sont valables
> `ADMIN_TOKEN_TTL_MINUTES` minutes (12 h par défaut).
