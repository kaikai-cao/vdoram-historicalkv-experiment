// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CollaborativeZkVm/ZkPrograms/ZkProgram.cs
// BLOB SHA: e291c76079f2f13939b9b25cca7568ca0aca8f1e

﻿namespace HuayiQi.CollaborativeZkVm.ZkPrograms;
public class ZkProgram {
    public required IReadOnlyList<ZkProgramOpcode> Opcodes { get; init; }

    static ZkProgram() => ZkProgramOpcodeJsonConverter.Initialize();
}
