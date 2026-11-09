'use strict';
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');
const crypto = require('crypto');

class AccessWorkload extends WorkloadModuleBase {
  async initializeWorkloadModule(w, t, r, args, sut, ctx) {
    await super.initializeWorkloadModule(w, t, r, args, sut, ctx);
    const prefix = `A${Date.now()}-R${r}-W${w}`;
    this.ids = [];
    for (let i = 0; i < this.roundArguments.parcels; i++) {
      const id = `${prefix}-${i}`;
      await this.sutAdapter.sendRequests({
        contractId: 'hybrid', contractFunction: 'RegisterData', invokerIdentity: 'User1',
        contractArguments: [id, crypto.randomBytes(32).toString('hex'), 'Org1MSP,Org2MSP'],
        readOnly: false
      });
      this.ids.push(id);
    }
  }
  async submitTransaction() {
    const id = this.ids[Math.floor(Math.random() * this.ids.length)];
    const fn = this.roundArguments.fn;
    await this.sutAdapter.sendRequests({
      contractId: 'hybrid', contractFunction: fn, invokerIdentity: 'User1',
      contractArguments: fn === 'RequestAccess' ? [id, 'bank-due-diligence'] : [id],
      readOnly: fn === 'QueryAuditTrail'
    });
  }
}
module.exports.createWorkloadModule = () => new AccessWorkload();
