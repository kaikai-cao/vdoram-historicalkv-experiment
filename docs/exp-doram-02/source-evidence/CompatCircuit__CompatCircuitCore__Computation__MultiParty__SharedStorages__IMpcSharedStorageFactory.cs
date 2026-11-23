// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/Computation/MultiParty/SharedStorages/IMpcSharedStorageFactory.cs
// BLOB SHA: 148a11bbbb6ba38b964abaa2d4a263acd286e840

﻿namespace HuayiQi.CompatCircuitCore.Computation.MultiParty.SharedStorages;
public interface IMpcSharedStorageFactory {
    public IMpcSharedStorage GetSharedStorage(IMpcSharedStorageSessionManager manager, int sessionID, int partyCount);
}
