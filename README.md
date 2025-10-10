# TchatRecoSong

Collecte et modération collaborative de recommandations musicales issues du tchat
Twitch.

## Lecture des commandes Twitch

### Vérification rapide de la branche

Le dépôt actif pointe sur la branche `work` dont le commit courant
(`1ea2910`) embarque toutes les modifications (API publique de
soumission, portail `/submit`, redirection du routeur Vue, etc.). Si tu
viens de fusionner ou de déployer, assure-toi que le service Render
utilise bien cette révision.

Twitch interdit d'envoyer des liens cliquables directement dans le tchat. Le bot
`!reco` doit donc se contenter d'afficher l'URL publique de la page "utilisateur"
hébergée par ce dépôt (ex. `https://tchatrecosong-front.onrender.com/submit`). Les viewers y collent
leur lien YouTube ou Spotify ; le backend va chercher les métadonnées
correspondantes via `POST /public/submissions/` et enregistre la recommandation
en base. Les écrans d'administration (liste des chansons, règles de
bannissement) restent réservés aux comptes Google autorisés.

## Base de données Neon / Render

Ton projet est déjà relié à une base Neon. Quand tu actives l'intégration GitHub depuis le dashboard Neon, une variable `NEON_DATABASE_URL` (ou `DATABASE_URL`) est ajoutée aux workflows GitHub Actions et peut être récupérée depuis l'onglet **Connect**. Copie cette URL et colle-la dans les variables d'environnement de Render (ou dans ton `.env` local). Elle contient déjà le `sslmode=require` nécessaire.

#### Mettre à jour la variable sur Render pas à pas

1. Ouvre ton service **Backend** sur Render.
2. Va dans l'onglet **Environment** puis clique sur **Add Environment Variable** (ou modifie la clé existante).
3. Renseigne `DATABASE_URL` comme nom, et colle l'URL Neon nettoyée (voir remarques ci-dessous) comme valeur.
4. Clique sur **Save Changes**, puis déclenche un redéploiement via **Manual Deploy > Deploy latest commit** pour que la nouvelle URL soit prise en compte.

> ❌ Neon affiche parfois un suffixe `&channel_binding=require`. Supprime-le : libpq/psycopg2 utilisé sur Render ne gère pas cette option et échouera avec une erreur d'authentification. Garde simplement `?sslmode=require` dans l'URL finale.

> ⚠️ Neon affiche souvent un exemple sous la forme `psql 'postgresql://...'`. Ne recopie que la partie `postgresql://…` (sans le préfixe `psql` ni les quotes), sinon la connexion échouera.


> 💡  Si tu préfères utiliser les champs détaillés (hôte, port, utilisateur…), Neon les expose aussi depuis l'onglet **Connection Details**. Tu peux alors définir `DATABASE_USER`, `DATABASE_PASSWORD`, etc. en local : le backend reconstruira automatiquement `DATABASE_URL` à partir de ces valeurs.

Pour initialiser les tables (`songs`, `ban_rules`) dans Neon, exécute le script SQL `backend/app/database/neon_schema.sql` via l'interface SQL Neon ou avec `psql`.

### Vérifier ta configuration localement

Avant de pousser sur Render, tu peux confirmer que les identifiants fournis sont valides en lançant :

```bash
cd backend
python -m app.database.connection
```

La commande exécute un `SELECT 1` sur la base ciblée et affiche les paramètres (sans le mot de passe) dans les logs. En cas d'échec, le message d'erreur SQLAlchemy est accompagné de l'hôte, du port et de l'utilisateur effectivement utilisés — pratique pour détecter une faute de frappe ou un mot de passe expiré.

### Utilisation avec Render PostgreSQL

- Render fournit plusieurs variables système, mais **seule** `DATABASE_URL` est lue par le backend. Assure-toi de mettre cette clé à jour dans l'onglet **Environment** après chaque rotation de mot de passe.
- Si tu renseignes manuellement les champs (`DATABASE_HOST`, `DATABASE_PORT`, ...), assure-toi que le nom d'hôte contient bien le domaine complet (ex. `dpg-...frankfurt-postgres.render.com`). L'erreur `could not translate host name` indiquée par SQLAlchemy signifie que l'hôte est tronqué.
- Un champ `sslmode` sera ajouté automatiquement (valeur `require` par défaut) si aucun paramètre n'est précisé. Tu peux le forcer via `DATABASE_SSLMODE=require` si ton hébergeur n'ajoute pas ce paramètre à l'URL.

## Configuration authentification & frontend

Chaque dossier (`backend/`, `frontend/`) contient un fichier `.env.example` à
copier en `.env` puis à personnaliser avant de lancer l'application ou de créer
les variables d'environnement sur Render. Les fichiers `.env` réels ne sont pas
versionnés : garde-les en local (ou sur Render) et ne les commits pas. Chaque clé
est commentée directement dans ces fichiers, mais voici un rappel synthétique :

| Variable | À renseigner avec... |
| --- | --- |
| `DATABASE_URL` | L'URL PostgreSQL fournie par Render (ou Neon) pour la base de données. C'est la seule clé lue par le backend en production. |
| `CORS_ORIGINS` | Les domaines autorisés à appeler l'API, séparés par des virgules. |
| `ADMIN_JWT_SECRET` | Une chaîne secrète longue et aléatoire pour signer les JWT admin. |
| `ADMIN_TOKEN_TTL_MINUTES` | Durée de validité des tokens admin (720 = 12 h). |
| `GOOGLE_CLIENT_ID` | L'identifiant OAuth Google obtenu dans Google Cloud Console. |
| `ALLOWED_GOOGLE_EMAILS` | Les emails Google autorisés à accéder à l'administration. |
| `VITE_API_URL` | L'URL publique du backend (ex : `https://tchat-reco-backend.onrender.com`). |
| `VITE_GOOGLE_CLIENT_ID` | Identique à `GOOGLE_CLIENT_ID` pour initialiser le bouton côté front. |
| `VITE_PUBLIC_VIEWER_URL` | L'URL à afficher dans le tchat Twitch (page publique de soumission, ex. `/submit`). |

> ⚠️ Les valeurs présentes dans les fichiers `.env` versionnés sont **des exemples**. Sur Render,
> remplace-les par tes propres identifiants (surtout `DATABASE_URL`, `ADMIN_JWT_SECRET`,
> les clients OAuth et les listes d'administrateurs). Un mot de passe erroné côté Neon ou Render
> provoquera un arrêt immédiat du backend.

### URLs frontend prêtes à l'emploi

- Portail public (viewers) : `https://tchatrecosong-front.onrender.com/submit`
- Page de connexion administrateur : `https://tchatrecosong-front.onrender.com/admin`
- Tableau de bord administrateur (après authentification) : `https://tchatrecosong-front.onrender.com/admin`
> ℹ️ Le tableau de bord admin demande une authentification Google. Assure-toi
> que l'adresse de chaque membre de l'équipe figure bien dans
> `ALLOWED_GOOGLE_EMAILS`.

> 💡 Les jetons générés par `POST /auth/google` sont valables
> `ADMIN_TOKEN_TTL_MINUTES` minutes (12 h par défaut). Ajustez cette valeur si besoin.

### Pourquoi `/submit` affiche "404 Not Found" après un rafraîchissement ?

Historiquement, le backend FastAPI n'exposait qu'une route `/`. Rafraîchir la
page `https://…/submit` envoyait donc la requête directement au backend et se
traduisait par un 404.

Depuis la mise à jour du backend, la route `/submit` renvoie automatiquement le
fichier `index.html` du build Vite si celui-ci est présent sur le serveur. Deux
conditions doivent toutefois être réunies :

1. **Le build frontend doit être disponible localement.** Par défaut, le backend
   cherche `frontend/dist/index.html`. Si ton pipeline de déploiement génère le
   build ailleurs, définis `FRONTEND_DIST_PATH` (et éventuellement
   `FRONTEND_INDEX_PATH`) pour pointer vers le dossier adéquat.
2. **Les assets du dossier `dist/assets` doivent être copiés avec le build.**
   Lorsque le dossier existe, le backend les expose automatiquement sous
   `https://…/assets/...`.

Si le fichier `index.html` n'est pas trouvé, la route `/submit` renvoie un code
503 explicite. Dans ce cas, vérifie que le build frontend est bien déployé à
côté de l'API ou mets à jour les variables d'environnement ci-dessus.

> 🌐 Tu déploies le frontend sur un service séparé (ex. Render) ? Renseigne
> `FRONTEND_SUBMIT_REDIRECT_URL` (ex. `https://tchatrecosong-front.onrender.com/submit`).
> Si le build local est absent, le backend redirigera automatiquement `/submit`
> vers cette URL pour éviter l'erreur 404 lors d'un rafraîchissement.

### Générer les identifiants et secrets OAuth

Impossible de te fournir des jetons ou des clients OAuth déjà valides — ces valeurs
doivent rester secrètes et spécifiques à ton compte. Voici comment les créer :

1. **Identifiants Google (`GOOGLE_CLIENT_ID` / `VITE_GOOGLE_CLIENT_ID`)**
   - Ouvre [console.cloud.google.com](https://console.cloud.google.com/).
   - Crée un projet (ou utilise-en un existant) puis active l'API "Google Identity Services".
   - Dans "Identifiants", crée un "ID client OAuth 2.0" de type Application Web.
   - Ajoute comme origines autorisées l'URL de ton frontend (Render) et `http://localhost:5173` pour les tests.
   - Copie l'ID client (pas besoin de secret côté frontend) et reporte-le dans `.env`.

2. **APIs YouTube & Spotify**
   - Le projet s'appuie sur les endpoints publics oEmbed de YouTube et Spotify, qui ne nécessitent ni clé API ni jeton d'accès supplémentaires.
   - Aucun champ `.env` n'est donc à renseigner pour ces services. Si tu souhaites étendre les fonctionnalités (ex : recherche), crée des clés via la Google Cloud Console ou le Dashboard Spotify Developer et ajuste le code en conséquence.
