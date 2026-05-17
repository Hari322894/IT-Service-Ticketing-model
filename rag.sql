CREATE TABLE IF NOT EXISTS support_tickets (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   category TEXT NOT NULL,
   issue_description TEXT NOT NULL
)