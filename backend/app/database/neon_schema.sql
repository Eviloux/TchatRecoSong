-- Schema initial pour l'instance Neon
-- Cette requête peut être exécutée via le tableau de bord SQL ou psql.

CREATE TABLE IF NOT EXISTS songs (
    id SERIAL PRIMARY KEY,
    title TEXT,
    artist TEXT,
    link TEXT UNIQUE,
    thumbnail TEXT,
    votes INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_songs_title ON songs (title);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs (artist);
CREATE INDEX IF NOT EXISTS idx_songs_link ON songs (link);

CREATE TABLE IF NOT EXISTS ban_rules (
    id SERIAL PRIMARY KEY,
    title TEXT,
    artist TEXT,
    link TEXT
);

CREATE INDEX IF NOT EXISTS idx_ban_rules_title ON ban_rules (title);
CREATE INDEX IF NOT EXISTS idx_ban_rules_artist ON ban_rules (artist);
CREATE INDEX IF NOT EXISTS idx_ban_rules_link ON ban_rules (link);

CREATE TABLE IF NOT EXISTS submission_requests (
    id SERIAL PRIMARY KEY,
    token VARCHAR(32) UNIQUE NOT NULL,
    twitch_user TEXT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    consumed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_submission_requests_token ON submission_requests (token);
