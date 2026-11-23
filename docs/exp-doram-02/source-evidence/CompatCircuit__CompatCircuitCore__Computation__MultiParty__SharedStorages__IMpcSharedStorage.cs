// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/Computation/MultiParty/SharedStorages/IMpcSharedStorage.cs
// BLOB SHA: f229e88a8d2576c245938954d5311c33959e0cca

﻿using HuayiQi.CompatCircuitCore.Computation.MultiParty.Messages;
using System.Numerics;

namespace HuayiQi.CompatCircuitCore.Computation.MultiParty.SharedStorages;
public interface IMpcSharedStorage {
    public int SessionID { get; }

    public int PartyCount { get; }

    public void UnregisterSession();

    public void HandleRawMessage(RawMessage message);

    public IReadOnlyList<bool> GetPartyOnlineAllParties();
    public void SetPartyOnline(int senderPartyIndex);

    public IReadOnlyList<bool> GetPartyCompletedAllParties();
    public void SetPartyCompleted(int senderPartyIndex);

    public IReadOnlyList<IReadOnlyList<BigInteger>?>? GetExposedBigIntegerShareVectorAllParties(string key);
    public void SetExposedBigIntegerShareVector(string key, int senderPartyIndex, IReadOnlyList<BigInteger> shares);

    public IReadOnlyList<IReadOnlyList<bool>?>? GetExposedBoolShareVectorAllParties(string key);
    public void SetExposedBoolShareVector(string key, int senderPartyIndex, IReadOnlyList<bool> shares);

    public IReadOnlyList<BigInteger>? GetInputShareVector(string key, int partyIndex);
    public void SetInputShareVector(string key, int senderPartyIndex, int receiverPartyIndex, IReadOnlyList<BigInteger> shares);
}
