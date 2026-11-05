-- SQLite Schema for Ontario Family Law Practice Intelligence (Per-Case Database)

CREATE TABLE IF NOT EXISTS case_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE NOT NULL,
    title TEXT,
    doc_type TEXT, -- Affidavit, Motion, Endorsement, Financial Statement, Correspondence, Disclosure, Exhibit
    doc_date TEXT, -- YYYY-MM-DD
    filing_party TEXT, -- Applicant, Respondent, Court, Third-Party
    page_count INTEGER DEFAULT 1,
    raw_path TEXT,
    text_path TEXT,
    is_scanned BOOLEAN DEFAULT 0,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search index across all extracted document texts
CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(
    filename,
    content,
    tokenize = 'porter unicode61'
);

CREATE TABLE IF NOT EXISTS timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date TEXT NOT NULL, -- YYYY-MM-DD
    event_time TEXT, -- e.g. 5:00 PM, 15:47, Evening
    title TEXT NOT NULL,
    location TEXT, -- Physical location or medium (Email, OFW, SMS)
    key_parties TEXT, -- Persons present
    category TEXT NOT NULL, -- Transition Conflict, Milestone, Disclosure Default, S7 Dispute, Communication
    description TEXT NOT NULL, -- Factual narrative with verbatim quotes
    child_impact TEXT, -- Child demeanour, reaction
    counsel_notes TEXT, -- Legal tactical observation, corroborating proof
    source_citation TEXT, -- Document filename, occurrence #, exhibit letter
    page_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search index for timeline events
CREATE VIRTUAL TABLE IF NOT EXISTS timeline_events_fts USING fts5(
    title,
    category,
    description,
    child_impact,
    counsel_notes,
    source_citation,
    location,
    key_parties,
    content='timeline_events',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS timeline_events_ai AFTER INSERT ON timeline_events BEGIN
    INSERT INTO timeline_events_fts(rowid, title, category, description, child_impact, counsel_notes, source_citation, location, key_parties)
    VALUES (new.id, new.title, new.category, new.description, new.child_impact, new.counsel_notes, new.source_citation, new.location, new.key_parties);
END;

CREATE TRIGGER IF NOT EXISTS timeline_events_ad AFTER DELETE ON timeline_events BEGIN
    INSERT INTO timeline_events_fts(timeline_events_fts, rowid, title, category, description, child_impact, counsel_notes, source_citation, location, key_parties)
    VALUES('delete', old.id, old.title, old.category, old.description, old.child_impact, old.counsel_notes, old.source_citation, old.location, old.key_parties);
END;

CREATE TRIGGER IF NOT EXISTS timeline_events_au AFTER UPDATE ON timeline_events BEGIN
    INSERT INTO timeline_events_fts(timeline_events_fts, rowid, title, category, description, child_impact, counsel_notes, source_citation, location, key_parties)
    VALUES('delete', old.id, old.title, old.category, old.description, old.child_impact, old.counsel_notes, old.source_citation, old.location, old.key_parties);
    INSERT INTO timeline_events_fts(rowid, title, category, description, child_impact, counsel_notes, source_citation, location, key_parties)
    VALUES (new.id, new.title, new.category, new.description, new.child_impact, new.counsel_notes, new.source_citation, new.location, new.key_parties);
END;

CREATE TABLE IF NOT EXISTS financial_disclosures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    party TEXT NOT NULL, -- Applicant or Respondent
    tax_year INTEGER,
    disclosure_type TEXT, -- NOA, T1, PayStub, Form 13 Line, S7 Expense
    line_item TEXT, -- e.g. "Line 15000 Total Income", "Gross Earnings Jan-Jun"
    declared_amount REAL,
    verified_amount REAL,
    variance REAL,
    discrepancy_notes TEXT,
    document_citation TEXT,
    page_number INTEGER
);

