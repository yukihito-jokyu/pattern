CREATE TABLE users (
    id         UUID         PRIMARY KEY,
    name       VARCHAR(50)  NOT NULL,
    email      VARCHAR(254) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ  NOT NULL
);
