'use strict';
const { Contract } = require('fabric-contract-api');

class HybridRegistry extends Contract {

  // Helpers starting with _ are not callable from outside.
  _now(ctx) {
    return ctx.stub.getDateTimestamp().toISOString(); // same on every peer
  }

  async _get(ctx, parcelId) {
    const key = ctx.stub.createCompositeKey('record', [parcelId]);
    const data = await ctx.stub.getState(key);
    if (!data || data.length === 0) {
      throw new Error(`Parcel ${parcelId} is not registered`);
    }
    return JSON.parse(data.toString('utf8'));
  }

  async _log(ctx, parcelId, action, outcome) {
    const key = ctx.stub.createCompositeKey('event', [parcelId, ctx.stub.getTxID()]);
    const event = {
      parcelId, action, outcome,
      by: ctx.clientIdentity.getMSPID(),
      at: this._now(ctx)
    };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(event)));
  }

  async RegisterData(ctx, parcelId, saltedHash, allowedMSPs) {
    const key = ctx.stub.createCompositeKey('record', [parcelId]);
    const existing = await ctx.stub.getState(key);
    if (existing && existing.length > 0) {
      throw new Error(`Parcel ${parcelId} is already registered`);
    }
    const record = {
      parcelId,
      saltedHash,                       // HMAC-SHA256; the salt stays off-chain
      allowedMSPs: allowedMSPs.split(','),
      registeredBy: ctx.clientIdentity.getMSPID(),
      registeredAt: this._now(ctx)
    };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(record)));
    await this._log(ctx, parcelId, 'REGISTER', 'GRANTED');
    return JSON.stringify(record);
  }

  async RequestAccess(ctx, parcelId, purpose) {
    const record = await this._get(ctx, parcelId);
    const granted = record.allowedMSPs.includes(ctx.clientIdentity.getMSPID());
    // A denial is logged too, so we return instead of throwing (throwing would discard the log).
    await this._log(ctx, parcelId, `ACCESS:${purpose}`, granted ? 'GRANTED' : 'DENIED');
    return JSON.stringify({ parcelId, granted, saltedHash: granted ? record.saltedHash : null });
  }

  async QueryAuditTrail(ctx, parcelId) {
    const iterator = ctx.stub.getStateByPartialCompositeKey('event', [parcelId]);
    const events = [];
    for await (const res of iterator) {
      events.push(JSON.parse(res.value.toString('utf8')));
    }
    return JSON.stringify(events);
  }
}

module.exports = HybridRegistry;
