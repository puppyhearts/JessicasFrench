CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sources (
  id SERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  root_path TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exam_series (
  id SERIAL PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  series_number INTEGER NOT NULL,
  title TEXT NOT NULL,
  pdf_path TEXT NOT NULL,
  pdf_start_page INTEGER,
  pdf_end_page INTEGER,
  audio_path TEXT,
  audio_duration_seconds REAL,
  status TEXT NOT NULL DEFAULT 'detected',
  UNIQUE(source_id, series_number)
);

CREATE TABLE IF NOT EXISTS questions (
  id SERIAL PRIMARY KEY,
  series_id INTEGER NOT NULL REFERENCES exam_series(id) ON DELETE CASCADE,
  question_number INTEGER NOT NULL,
  section TEXT NOT NULL,
  prompt TEXT NOT NULL,
  instructions TEXT,
  correct_answer CHAR(1),
  page_number INTEGER,
  confidence REAL NOT NULL DEFAULT 0,
  UNIQUE(series_id, question_number)
);

CREATE TABLE IF NOT EXISTS answer_choices (
  id SERIAL PRIMARY KEY,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  label CHAR(1) NOT NULL,
  text TEXT NOT NULL,
  UNIQUE(question_id, label)
);

CREATE TABLE IF NOT EXISTS audio_segments (
  id SERIAL PRIMARY KEY,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  start_seconds REAL NOT NULL,
  end_seconds REAL NOT NULL,
  confidence REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transcripts (
  id SERIAL PRIMARY KEY,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  sentences JSONB NOT NULL DEFAULT '[]',
  words JSONB NOT NULL DEFAULT '[]',
  vtt_path TEXT,
  srt_path TEXT
);

CREATE TABLE IF NOT EXISTS attempts (
  id SERIAL PRIMARY KEY,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  selected_answer CHAR(1) NOT NULL,
  is_correct BOOLEAN NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id SERIAL PRIMARY KEY,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  summary JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS embeddings (
  id SERIAL PRIMARY KEY,
  question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL,
  entity_text TEXT NOT NULL,
  embedding vector(1536)
);
