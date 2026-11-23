// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/Computation/IMpcExecutor.cs
// BLOB SHA: 7a043675bbfc558b8b3203dc2d896a140fc5f162

﻿using HuayiQi.CompatCircuitCore.Arithmetic;
using HuayiQi.CompatCircuitCore.CompatCircuits.MpcCircuits;
using HuayiQi.CompatCircuitCore.MultiPartyComputationPrimitives;

namespace HuayiQi.CompatCircuitCore.Computation;
public interface IMpcExecutor {
    public Task<CircuitExecuteResult> Compute(MpcCircuit mpcCircuit, IReadOnlyDictionary<int, Field> publicInputValueDict, IReadOnlyDictionary<int, MpcValue> privateInputValueShareDict);
}