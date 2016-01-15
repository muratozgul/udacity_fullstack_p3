CREATE TABLE IF NOT EXISTS categories (
  id          INTEGER  PRIMARY KEY AUTOINCREMENT NOT NULL,
  name        TEXT  NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
  id          INTEGER  PRIMARY KEY AUTOINCREMENT NOT NULL,
  category_id INTEGER,
  name        TEXT  NOT NULL,
  description TEXT,
  FOREIGN KEY(category_id) REFERENCES categories(id)
);