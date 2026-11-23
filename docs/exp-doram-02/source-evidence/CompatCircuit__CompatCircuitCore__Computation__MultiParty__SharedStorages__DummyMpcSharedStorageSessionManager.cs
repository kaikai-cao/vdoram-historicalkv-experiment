// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/Computation/MultiParty/SharedStorages/DummyMpcSharedStorageSessionManager.cs
// BLOB SHA: 8d0bfb50506d3860e1879be103b1180a5f4b7a67

﻿using HuayiQi.CompatCircuitCore.Computation.MultiParty.Messages;
using HuayiQi.CompatCircuitCore.Computation.MultiParty.Network;

namespace HuayiQi.CompatCircuitCore.Computation.MultiParty.SharedStorages;
public class DummyMpcSharedStorageSessionManager : IMpcSharedStorageSessionManager {
    public IMpcClient MpcClient { get; }
    public void HandleRawMessage(RawMessage message) { }
    public void RegisterSession(int sessionID, IMpcSharedStorage sharedStorage) { }
    public void UnregisterSession(int sessionID) { }
    public DummyMpcSharedStorageSessionManager() => this.MpcClient = new DummyMpcClient();
    public DummyMpcSharedStorageSessionManager(IMpcClient mpcClient) => this.MpcClient = mpcClient;
}
