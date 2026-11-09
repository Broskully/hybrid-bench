'use strict';
// Usage: node e2e.js fabric   or   node e2e.js postgres
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { performance } = require('perf_hooks');
const Minio = require('minio');
const { Client: PgClient } = require('pg');
const grpc = require('@grpc/grpc-js');
const { connect, hash, signers } = require('@hyperledger/fabric-gateway');

const SIZES = [10 * 1024, 1024 * 1024, 10 * 1024 * 1024]; // 10 KB, 1 MB, 10 MB
const RUNS = Number(process.env.RUNS || 200);               // per size

const minio = new Minio.Client({ endPoint: 'localhost', port: 9000, useSSL: false,
  accessKey: 'bench', secretKey: 'benchpass123' });

async function connectPostgres() {
  const pg = new PgClient({ host: 'localhost', user: 'postgres', password: 'benchpass', database: 'postgres' });
  await pg.connect();
  return {
    async register(parcelId, saltedHash, orgs) {
      await pg.query('BEGIN');
      await pg.query('INSERT INTO records(parcel_id, salted_hash, allowed_orgs, registered_by) VALUES ($1,$2,$3,$4)',
        [parcelId, saltedHash, orgs.split(','), 'Org1MSP']);
      await pg.query('INSERT INTO events(parcel_id, action, outcome, by_org) VALUES ($1,$2,$3,$4)',
        [parcelId, 'REGISTER', 'GRANTED', 'Org1MSP']);
      await pg.query('COMMIT');
    },
    close: () => pg.end()
  };
}

async function connectFabric() {
  const org = path.join(process.env.HOME, 'hybrid-bench/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com');
  const user = path.join(org, 'users/User1@org1.example.com/msp');
  const client = new grpc.Client('localhost:7051',
    grpc.credentials.createSsl(fs.readFileSync(path.join(org, 'peers/peer0.org1.example.com/tls/ca.crt'))),
    { 'grpc.ssl_target_name_override': 'peer0.org1.example.com' });
  const gateway = connect({
    client,
    identity: { mspId: 'Org1MSP', credentials: fs.readFileSync(path.join(user, 'signcerts/User1@org1.example.com-cert.pem')) },
    signer: signers.newPrivateKeySigner(crypto.createPrivateKey(fs.readFileSync(path.join(user, 'keystore/priv_sk')))),
    hash: hash.sha256
  });
  const contract = gateway.getNetwork('mychannel').getContract('hybrid');
  return {
    register: (p, h, o) => contract.submitTransaction('RegisterData', p, h, o),
    close: () => { gateway.close(); client.close(); }
  };
}

async function main() {
  const mode = process.argv[2];
  const ledger = mode === 'fabric' ? await connectFabric() : await connectPostgres();
  if (!(await minio.bucketExists('docs'))) await minio.makeBucket('docs');
  const rows = [];
  for (const size of SIZES) {
    for (let i = 0; i < RUNS; i++) {
      const parcelId = `${mode}-${size}-${Date.now()}-${i}`;
      const doc = crypto.randomBytes(size);
      const salt = crypto.randomBytes(32);
      const t0 = performance.now();
      const saltedHash = crypto.createHmac('sha256', salt).update(doc).digest('hex');
      const t1 = performance.now();
      await minio.putObject('docs', `doc/${parcelId}`, doc);
      await minio.putObject('docs', `salt/${parcelId}`, salt);   // salt stays off-chain
      const t2 = performance.now();
      await ledger.register(parcelId, saltedHash, 'Org1MSP,Org2MSP');
      const t3 = performance.now();
      rows.push([mode, size, i, (t1 - t0).toFixed(3), (t2 - t1).toFixed(3),
                 (t3 - t2).toFixed(3), (t3 - t0).toFixed(3)].join(','));
    }
  }
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  fs.writeFileSync(`e2e-${mode}-${stamp}.csv`,
    'mode,size_bytes,run,hash_ms,offchain_ms,ledger_ms,total_ms\n' + rows.join('\n'));
  await ledger.close();
}

main().catch(err => { console.error(err); process.exit(1); });
