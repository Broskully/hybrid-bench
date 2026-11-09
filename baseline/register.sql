\set n random(1, 1000000000)
BEGIN;
INSERT INTO records VALUES ('pg-' || :n, 'hash', '{Org1MSP,Org2MSP}', 'Org1MSP', now())
  ON CONFLICT DO NOTHING;
INSERT INTO events(parcel_id, action, outcome, by_org)
  VALUES ('pg-' || :n, 'REGISTER', 'GRANTED', 'Org1MSP');
END;
