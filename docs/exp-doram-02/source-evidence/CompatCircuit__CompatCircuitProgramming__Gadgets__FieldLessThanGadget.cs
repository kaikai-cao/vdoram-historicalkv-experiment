// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitProgramming/Gadgets/FieldLessThanGadget.cs
// BLOB SHA: ed1d0f7dc5791869db9136ef9ab7e0f0bb436a70

﻿using HuayiQi.CompatCircuitProgramming.CircuitElements;
using System.Diagnostics;

namespace HuayiQi.CompatCircuitProgramming.Gadgets;
public class FieldLessThanGadget : IGadget {
    public List<string> GetInputWireNames() => ["left", "right"];
    public List<string> GetOutputWireNames() => ["is_less_than"];
    public GadgetInstance ApplyGadget(IReadOnlyList<Wire> inputWires, string namePrefix) {
        if (inputWires.Count != 2) {
            throw new ArgumentException("Unexpected element count", nameof(inputWires));
        }

        GadgetIncompleteCircuitBoard circuitBoard = new();

        IReadOnlyList<Wire> leftBits;
        {
            GadgetInstance ins = new BitDecompositionGadget().ApplyGadget([inputWires[0]], $"{namePrefix}_[field_less_than]_left_bits");
            ins.Save(circuitBoard);
            leftBits = ins.OutputWires;
        }

        IReadOnlyList<Wire> rightBits;
        {
            GadgetInstance ins = new BitDecompositionGadget().ApplyGadget([inputWires[1]], $"{namePrefix}_[field_less_than]_right_bits");
            ins.Save(circuitBoard);
            rightBits = ins.OutputWires;
        }

        int bitSize = leftBits.Count;
        Trace.Assert(leftBits.Count == rightBits.Count);

        Wire outputWire;
        {
            GadgetInstance ins = new BitsLessThanGadget(bitSize).ApplyGadget([.. leftBits, .. rightBits], $"{namePrefix}_[field_less_than]_bits_less_than");
            ins.Save(circuitBoard);
            outputWire = ins.OutputWires[0];
        }

        return GadgetIncompleteCircuitBoardHelper.NewGadgetInstanceFromGadgetIncompleteCircuitBoard([outputWire], circuitBoard);
    }
}