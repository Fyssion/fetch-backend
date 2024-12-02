CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY, -- our ROWID alias, auto increments
    payer TEXT NOT NULL,
    points INTEGER NOT NULL,
    timestamp TEXT NOT NULL
);
