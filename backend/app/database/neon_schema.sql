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
