# Lecture des commandes `!reco` dans le tchat Twitch

Ce dépôt contient un utilitaire Python pour écouter les commandes `!reco`
depuis un salon Twitch via l'interface IRC officielle.  Cette approche repose sur
une connexion WebSocket, ne nécessite pas de webhook EventSub et reste compatible
avec un hébergement simple (Docker, VM ou machine locale).

## 1. Pré-requis OAuth

1. Créez une application dans le [Twitch Developer Console](https://dev.twitch.tv/console/apps).
2. Ajoutez une URL de redirection (par exemple `http://localhost:3000/auth/twitch`).
3. Générez un **OAuth user access token** avec les scopes `chat:read` et `chat:edit`.
   Vous pouvez utiliser l'outil officiel [Twitch Token Generator](https://twitchtokengenerator.com/)
   ou réaliser le flux manuellement avec `https://id.twitch.tv/oauth2/authorize`.
4. Conservez le jeton sous la forme `oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.

## 2. Installation des dépendances

```bash
cd backend
pip install -r requirements.txt
```

Le fichier `requirements.txt` inclut désormais la dépendance `websockets` utilisée
pour établir la connexion IRC.

## 3. Lecture des commandes

Le module `backend/app/services/twitch_chat_listener.py` expose la classe
`TwitchChatListener`.  L'exemple minimal ci-dessous affiche l'utilisateur et le
commentaire accompagnant chaque commande `!reco`.

```python
import asyncio
from backend.app.services import TwitchChatListener

async def main():
    listener = TwitchChatListener(
        channel="nom_de_votre_chaine",
        username="nom_du_compte_bot",
        oauth_token="oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    async for command in listener.watch_commands():
        print(command.user, command.comment)

asyncio.run(main())
```

Vous pouvez également définir les variables d'environnement `TWITCH_USERNAME` et
`TWITCH_OAUTH_TOKEN` avant d'instancier le listener.

## 4. Création de tickets de soumission

Dans la nouvelle architecture, le message `!reco` déclenche la génération d'un
ticket temporaire côté backend. Ce ticket fournit un lien unique vers le formulaire
frontend où le viewer peut coller un lien YouTube ou Spotify.

```python
from backend.app.services import TwitchChatListener
from backend.app.crud import submission_request
from backend.app.database.connection import SessionLocal

listener = TwitchChatListener(channel="votre_chaine")

async def enqueue_commands():
    async for command in listener.watch_commands():
        with SessionLocal() as session:
            submission_request.create_request(
                session,
                twitch_user=command.user,
                comment=command.comment,
                ttl_minutes=5,
            )
```

Le frontend (voir `frontend/src/views/SubmissionView.vue`) consomme ensuite ces
tickets via l'endpoint `/requests/{token}` et dépose le lien du viewer sur
`/requests/{token}/submit`. Le backend se charge de récupérer les métadonnées via
les oEmbed YouTube/Spotify avant d'enregistrer la recommandation.
