# Déploiement sur Render (gratuit, back toujours éveillé)

Objectif : un front qui ne s'endort jamais et un back qui reste éveillé, sans payer.

| Élément | Type Render | Pourquoi |
|---|---|---|
| Front (Vue) | **Static Site** | Gratuit, servi par un CDN, ne s'endort jamais, ne consomme pas d'heures. |
| Back (FastAPI) | **Web Service** (free) | Gardé éveillé par un ping externe sur `/health` toutes les 10 min. |
| Base | Neon (inchangé) | Se réveille en moins d'une seconde, ce n'est pas gênant. |

> Les limites du plan gratuit (mise en veille après ~15 min sans requête, 750 h/mois
> partagées entre les services) peuvent évoluer : vérifie la page « Free » de la doc
> Render. Un seul service allumé en permanence fait ~744 h/mois, d'où l'intérêt de
> sortir le front des heures consommées.

`render.yaml` à la racine décrit cette configuration (utilisable comme Blueprint).
Ce guide décrit la même chose via le tableau de bord, puisque les services existants
y ont été créés à la main.

---

## 1. Créer le front en Static Site

Un Web Service ne peut pas être converti en Static Site : on crée un nouveau service,
on le teste, puis on bascule. L'ancien front reste en ligne pendant ce temps.

**New + → Static Site**, puis le dépôt `Eviloux/TchatRecoSong`, branche `main` :

| Champ | Valeur |
|---|---|
| Name | `TchatRecoSong-web` (donne l'URL `https://tchatrecosong-web.onrender.com`, ou proche si le nom est pris) |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |

**Environment** :

| Variable | Valeur |
|---|---|
| `NODE_VERSION` | `22` |
| `VITE_API_URL` | URL du back, ex. `https://tchatrecosong.onrender.com` (sans `/` final) |
| `VITE_GOOGLE_CLIENT_ID` | optionnel (le front le récupère aussi via l'API) |
| `VITE_TWITCH_CLIENT_ID` | optionnel (idem) |

**Redirects/Rewrites** (indispensable, sinon `/submit`, `/admin` et `/login` donnent une 404) :

| Source | Destination | Action |
|---|---|---|
| `/*` | `/index.html` | **Rewrite** |

**Headers** (path `/*` pour chacun) :

| Nom | Valeur |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

Les variables `VITE_*` sont intégrées au moment du build : après les avoir modifiées,
relance un déploiement (**Manual Deploy → Deploy latest commit**).

## 2. Autoriser la nouvelle URL partout

Remplace `<nouvelle-url>` par l'URL du Static Site, par ex. `https://tchatrecosong-web.onrender.com`.

1. **Back Render → Environment → `CORS_ORIGINS`** : ajoute la nouvelle URL en gardant
   l'ancienne pendant la transition, séparées par une virgule, sans `/` final :
   `https://tchatrecosong-front.onrender.com,<nouvelle-url>`
2. **Twitch** (dev.twitch.tv → ton application → OAuth Redirect URLs) : ajoute
   `<nouvelle-url>/login`.
3. **Google Cloud Console → Clients → ton client Web → Origines JavaScript autorisées** :
   ajoute `<nouvelle-url>`.
4. Si `FRONTEND_SUBMIT_REDIRECT_URL` est défini sur le back, mets-le à `<nouvelle-url>/submit`.

## 3. Régler le back

Dans le service back existant :

| Réglage | Valeur |
|---|---|
| Settings → **Health Check Path** | `/health` |
| Environment → `PYTHON_VERSION` | `3.13.4` (évite qu'une nouvelle version de Python change sans prévenir) |
| Environment → `TRUSTED_PROXY_COUNT` | `1` |

Le Build Command (`pip install -r requirements.txt`) et le Start Command
(`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, avec Root Directory `backend`)
restent ceux qui fonctionnent aujourd'hui.

## 4. Garder le back éveillé (cron-job.org)

1. Crée un compte gratuit sur [cron-job.org](https://cron-job.org).
2. **Create cronjob** :
   - URL : `https://<url-du-back>/health` (pas `/`, qui redirige vers le front)
   - Schedule : **toutes les 10 minutes**
   - Notifications : coche « en cas d'échec », pour être prévenu si le back tombe.
3. Vérifie dans l'historique du cronjob que les appels répondent `200`.

`/health` ne touche pas la base : le ping ne réveille pas Neon et ne coûte rien.

## 5. Tester puis basculer

Sur `<nouvelle-url>` :

- [ ] La page d'accueil et `<nouvelle-url>/submit` s'affichent (y compris après un rafraîchissement).
- [ ] Une chanson s'envoie, la liste se met à jour, le vote fonctionne.
- [ ] Le badge « En live / Hors ligne » s'affiche.
- [ ] Connexion admin Twitch et Google OK sur `<nouvelle-url>/login`.
- [ ] Interrupteur de thème clair/sombre OK.

Puis :

1. Mets à jour le lien partagé dans le tchat (commande `!reco`, panneaux Twitch) vers `<nouvelle-url>/submit`.
2. Après quelques jours, supprime l'ancien service `TchatRecoSong-front` (Web Service Node),
   retire l'ancienne URL de `CORS_ORIGINS`, de Twitch et de Google.
3. Optionnel : supprime `frontend/server.js` et le script `start` de `frontend/package.json`,
   devenus inutiles.

## Alternative : garder l'URL actuelle

L'URL `.onrender.com` dépend du nom donné à la création. Pour garder
`tchatrecosong-front.onrender.com`, il faudrait supprimer l'ancien service avant de créer
le Static Site avec le même nom, sans garantie que le nom soit immédiatement disponible,
et avec une coupure le temps du déploiement. La migration ci-dessus évite ce risque.
Un nom de domaine personnalisé (quelques euros par an) rendrait l'URL indépendante de Render.
