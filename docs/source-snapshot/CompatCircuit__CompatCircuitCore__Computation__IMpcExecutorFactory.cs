// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/Computation/IMpcExecutorFactory.cs
// BLOB SHA: 8983b236f073f5f7c51a3c0e335948dae735150e

﻿namespace HuayiQi.CompatCircuitCore.Computation;

public interface IMpcExecutorFactory {
    public IMpcExecutor NextExecutor();
}