// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/MultiPartyComputationPrimitives/MpcValue.cs
// BLOB SHA: 0932697ce7fcd9341181aed1bf58c4174b705d22

﻿using HuayiQi.CompatCircuitCore.Arithmetic;
using System.Diagnostics.CodeAnalysis;

namespace HuayiQi.CompatCircuitCore.MultiPartyComputationPrimitives;
public record MpcValue {
    public required Field Value { get; init; }
    public required bool IsSecretShare { get; init; }
    public MpcValue() { }

    [SetsRequiredMembers]
    public MpcValue(Field value, bool isSecretShare) {
        this.Value = value;
        this.IsSecretShare = isSecretShare;
    }

    public Field AssumeNonShare() => this.IsSecretShare ? throw new Exception("This MpcValue is a secret share") : this.Value;
}
