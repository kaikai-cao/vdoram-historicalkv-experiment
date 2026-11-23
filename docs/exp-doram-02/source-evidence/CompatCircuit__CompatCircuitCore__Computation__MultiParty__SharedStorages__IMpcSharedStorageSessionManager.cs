// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/Computation/MultiParty/SharedStorages/IMpcSharedStorageSessionManager.cs
// BLOB SHA: 7002cc8dbf055aa1cccfad2fff528e651aeeb74d

﻿using HuayiQi.CompatCircuitCore.Computation.MultiParty.Messages;
using HuayiQi.CompatCircuitCore.Computation.MultiParty.Network;

namespace HuayiQi.CompatCircuitCore.Computation.MultiParty.SharedStorages;
public interface IMpcSharedStorageSessionManager {
    public void HandleRawMessage(RawMessage message);
    public void RegisterSession(int sessionID, IMpcSharedStorage sharedStorage);
    public void UnregisterSession(int sessionID);
    public IMpcClient MpcClient { get; }
}