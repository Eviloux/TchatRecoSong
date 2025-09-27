# TchatRecoSong

Collecte et modération collaborative de recommandations musicales issues du tchat
Twitch.

## Lecture des commandes Twitch

Pour lire automatiquement les commandes `!reco` depuis le tchat de votre chaîne,
consultez le guide [`docs/twitch_chat_commands.md`](docs/twitch_chat_commands.md).

Le bot n'attend plus de lien directement dans le tchat (Twitch les bloque). À la
place, chaque `!reco` ouvre un ticket temporaire consommable depuis le frontend :

1. `POST /requests/` (côté bot/admin) crée un ticket et renvoie un token.
2. Répondez dans Twitch avec l'URL publique du portail viewer (ex. `https://wizbit.example/reco`).
3. Le frontend "utilisateur" liste les tickets actifs : le viewer retrouve son pseudo, ouvre le formulaire `submit/<token>` et colle un lien YouTube ou Spotify.
4. Le backend récupère les
   métadonnées (titre, artiste, miniature) via oEmbed et alimente la base.
5. Les features d'administration (validation de la liste, ajout de ban words)
   sont protégées derrière un login Google ou Twitch.

## Base de données Neon

Le backend FastAPI est désormais prêt à se connecter à l'instance Neon fournie par défaut. Si aucune variable d'environnement `DATABASE_URL` n'est définie, la connexion utilisera automatiquement l'URL suivante :

```
postgresql://neondb_owner:npg_ljrtUWJ9o7Cs@ep-plain-leaf-ag9ynkn2-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

Pour initialiser les tables (`songs`, `ban_rules`, `submission_requests`) directement dans Neon, importez le fichier SQL `backend/app/database/neon_schema.sql` via l'outil SQL du tableau de bord Neon ou avec `psql`.

## Configuration authentification & frontend

Les variables suivantes pilotent les accès administrateur et le portail frontend :

| Variable | Description |
| --- | --- |
| `ADMIN_JWT_SECRET` | Secret HMAC pour signer les jetons admin (obligatoire en production). |
| `ALLOWED_GOOGLE_EMAILS` | Liste (séparée par des virgules) des adresses Google autorisées. |
| `ALLOWED_TWITCH_LOGINS` | Liste des logins Twitch autorisés. |
| `GOOGLE_CLIENT_ID` | Client ID OAuth Google utilisé pour vérifier les `credential`. |
| `TWITCH_CLIENT_ID` | Client ID OAuth Twitch pour valider les tokens. |
| `SUBMISSION_TTL_MINUTES` | Durée de validité des tickets `!reco` (défaut : 5 minutes). |
| `VITE_API_URL` | URL du backend, consommée par le frontend (ex : `http://localhost:8000`). |
| `VITE_GOOGLE_CLIENT_ID` | Même valeur que côté backend pour initialiser le bouton Google. |
| `VITE_TWITCH_CLIENT_ID` | Identifiant Twitch utilisé pour l'implicit flow côté frontend. |
| `VITE_PUBLIC_VIEWER_URL` | (Optionnel) URL absolue à afficher dans le tchat Twitch ; utilisée pour générer les liens copiables dans l'interface. |

> 💡 Les jetons générés par `POST /auth/google` et `POST /auth/twitch` sont valables
> `ADMIN_TOKEN_TTL_MINUTES` minutes (12 h par défaut).
