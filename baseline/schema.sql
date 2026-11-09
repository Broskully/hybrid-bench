CREATE TABLE records (
  parcel_id     TEXT PRIMARY KEY,   -- duplicate parcel IDs rejected, as in the contract
  salted_hash   TEXT NOT NULL,
  allowed_orgs  TEXT[] NOT NULL,
  registered_by TEXT NOT NULL,
  registered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE events (
  id        BIGSERIAL PRIMARY KEY,
  parcel_id TEXT NOT NULL,
  action    TEXT NOT NULL,
  outcome   TEXT NOT NULL,
  by_org    TEXT NOT NULL,
  at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX events_parcel ON events(parcel_id);
