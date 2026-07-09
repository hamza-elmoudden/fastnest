-- ══════════════════════════════════════════════════════
--  FastNest Demo — PostgreSQL Schema
-- ══════════════════════════════════════════════════════

-- Run with:
--   psql -U postgres -d fastnest_db -f schema.sql
-- Or create db first:
--   psql -U postgres -c "CREATE DATABASE fastnest_db;"
--   psql -U postgres -d fastnest_db -f schema.sql

-- ══════════════════════════════════════════════════════
--  RESET (run this before re-seeding):
-- ══════════════════════════════════════════════════════
-- TRUNCATE posts, refresh_tokens, users RESTART IDENTITY CASCADE;
--
--  Password for all seed users: secret123
--  Hashed with PBKDF2-HMAC-SHA256, 200,000 iterations, per-row random salt
--  (see example/example/utils/security.py:hash_password) — demo/seed values
--  only, not real credentials.
-- ══════════════════════════════════════════════════════

-- ── Extensions ──────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Enums ────────────────────────────────────────────
CREATE TYPE user_role AS ENUM ('admin', 'user', 'moderator');

-- ── Tables ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id            UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(255)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    password_salt VARCHAR(64)   NOT NULL,
    roles         user_role[]   NOT NULL DEFAULT '{user}',
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posts (
    id         UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    title      VARCHAR(255) NOT NULL,
    content    TEXT         NOT NULL,
    author_id  UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT        NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indexes ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email      ON users(email);
CREATE INDEX IF NOT EXISTS idx_posts_author_id  ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);

-- ── Auto-update updated_at ────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER posts_updated_at
    BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Seed Data ─────────────────────────────────────────
-- Password for all seed users: "secret123"
-- password_hash/password_salt below are PBKDF2-HMAC-SHA256 (200,000 iterations)
-- of "secret123", generated via:
--   python3 -c "from example.example.utils.security import hash_password; print(hash_password('secret123'))"

INSERT INTO users (name, email, password_hash, password_salt, roles) VALUES
    ('Admin User',    'admin@fastnest.dev', 'ae1a300122076fa9431f3e5cf7f0f195f0c9bde2b90ab0151efbf40d7e1f1806', '0a590ebd44abd760ab2e9ddce718b0f9', '{admin,user}'),
    ('Regular User',  'user@fastnest.dev',  'ae1a300122076fa9431f3e5cf7f0f195f0c9bde2b90ab0151efbf40d7e1f1806', '0a590ebd44abd760ab2e9ddce718b0f9', '{user}'),
    ('Moderator',     'mod@fastnest.dev',   'ae1a300122076fa9431f3e5cf7f0f195f0c9bde2b90ab0151efbf40d7e1f1806', '0a590ebd44abd760ab2e9ddce718b0f9', '{moderator,user}')
ON CONFLICT (email) DO NOTHING;

INSERT INTO posts (title, content, author_id)
SELECT
    'Post ' || g,
    'Content of post number ' || g || '. Written by admin.',
    (SELECT id FROM users WHERE email = 'admin@fastnest.dev')
FROM generate_series(1, 5) g
ON CONFLICT DO NOTHING;

-- ── Verify ────────────────────────────────────────────
SELECT 'users'  AS table_name, COUNT(*) FROM users
UNION ALL
SELECT 'posts'  AS table_name, COUNT(*) FROM posts;