# TchatRecoSong

Listing of recommended songs by Twitch tchat.

## Base de données Neon

Le backend FastAPI est désormais prêt à se connecter à l'instance Neon fournie par défaut. Si aucune variable d'environnement `DATABASE_URL` n'est définie, la connexion utilisera automatiquement l'URL suivante :

```
postgresql://neondb_owner:npg_ljrtUWJ9o7Cs@ep-plain-leaf-ag9ynkn2-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

Pour initialiser les tables (`songs` et `ban_rules`) directement dans Neon, importez le fichier SQL `backend/app/database/neon_schema.sql` via l'outil SQL du tableau de bord Neon ou avec `psql`.
