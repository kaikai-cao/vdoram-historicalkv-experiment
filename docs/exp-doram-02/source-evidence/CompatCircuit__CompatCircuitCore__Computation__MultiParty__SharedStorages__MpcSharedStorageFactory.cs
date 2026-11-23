// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/Computation/MultiParty/SharedStorages/MpcSharedStorageFactory.cs
// BLOB SHA: a2a11518047d62d0dbcc81728a05537788bd43bb

﻿namespace HuayiQi.CompatCircuitCore.Computation.MultiParty.SharedStorages;
public class MpcSharedStorageFactory : IMpcSharedStorageFactory {
    public MpcSharedStorage GetSharedStorage(IMpcSharedStorageSessionManager manager, int sessionID, int partyCount) => new(manager, sessionID, partyCount);
    IMpcSharedStorage IMpcSharedStorageFactory.GetSharedStorage(IMpcSharedStorageSessionManager manager, int sessionID, int partyCount) => this.GetSharedStorage(manager, sessionID, partyCount);
}
