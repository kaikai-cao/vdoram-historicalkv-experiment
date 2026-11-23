// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CollaborativeZkVm/ZkPrograms/ZkProgramInstance.cs
// BLOB SHA: 52e8778251d422c739c68f53ce7b5b430ca5cfb1

﻿using HuayiQi.CompatCircuitCore.Arithmetic;

namespace HuayiQi.CollaborativeZkVm.ZkPrograms;
public class ZkProgramInstance : ZkProgram {
    public required int MyID { get; init; }
    public required int PartyCount { get; init; }
    public required IReadOnlyList<Field> PublicInputs { get; init; }
    public required IReadOnlyList<Field> PrivateInputShares { get; init; }

    public required int GlobalStepsNoMoreThan { get; init; }

    static ZkProgramInstance() => ZkProgramOpcodeJsonConverter.Initialize();
}
