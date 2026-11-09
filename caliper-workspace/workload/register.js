'use strict';
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');
const crypto = require('crypto');

class RegisterWorkload extends WorkloadModuleBase {
  constructor() { super(); this.txIndex = 0; }
  async submitTransaction() {
    this.txIndex++;
    const parcelId = `R${this.roundIndex}-W${this.workerIndex}-${this.txIndex}-${Date.now()}`;
    await this.sutAdapter.sendRequests({
      contractId: 'hybrid',
      contractFunction: 'RegisterData',
      invokerIdentity: 'User1',
      contractArguments: [parcelId, crypto.randomBytes(32).toString('hex'), 'Org1MSP,Org2MSP'],
      readOnly: false
    });
  }
}
module.exports.createWorkloadModule = () => new RegisterWorkload();
