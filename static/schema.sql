-- schema.sql - Structure de la base de données optimisée

DROP TABLE IF EXISTS liens;
DROP TABLE IF EXISTS images;
DROP TABLE IF EXISTS objets;
DROP TABLE IF EXISTS login_attempts;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS auth_logs;

CREATE TABLE objets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    description TEXT,
    categorie TEXT,
    fabricant TEXT,
    date_fabrication TEXT,
    numero_inventaire TEXT UNIQUE NOT NULL, -- Contrainte UNIQUE essentielle
    image_principale TEXT,
    etat TEXT,
    date_ajout TEXT NOT NULL,
    date_modification TEXT DEFAULT NULL,
    attributs_specifiques TEXT,
    version INTEGER DEFAULT 1 -- Pour le verrouillage optimiste
);

CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objet_id INTEGER NOT NULL,
    chemin TEXT NOT NULL,
    legende TEXT,
    ordre INTEGER DEFAULT 0,
    FOREIGN KEY (objet_id) REFERENCES objets (id) ON DELETE CASCADE
);

CREATE TABLE liens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objet_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    titre TEXT,
    ordre INTEGER DEFAULT 0,
    FOREIGN KEY (objet_id) REFERENCES objets (id) ON DELETE CASCADE
);

CREATE TABLE login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    attempts INTEGER DEFAULT 1,
    locked_until TIMESTAMP,
    last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(username, ip_address)
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE auth_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
