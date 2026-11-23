// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CollaborativeZkVm/ZkPrograms/ZkProgramExecuteResult.cs
// BLOB SHA: eaab332cab06ca320988d246b6a8f2b511ef6f28

﻿using HuayiQi.CompatCircuitCore.Arithmetic;

namespace HuayiQi.CollaborativeZkVm.ZkPrograms;
public class ZkProgramExecuteResult {
    public required IReadOnlyList<Field> PublicOutputs { get; init; }
    public required int GlobalStepCounter { get; init; }
    public required TimeSpan TotalTime { get; init; }
    public required IReadOnlyDictionary<string, TimeSpan> StepTimes { get; init; }
}
