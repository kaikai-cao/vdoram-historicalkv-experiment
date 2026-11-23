// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitProgramming/Gadgets/FieldGreaterEqualThanGadget.cs
// BLOB SHA: 66d4a996d2b909d07d0310d42b2a58376fface39

﻿using HuayiQi.CompatCircuitProgramming.CircuitElements;

namespace HuayiQi.CompatCircuitProgramming.Gadgets;
public class FieldGreaterEqualThanGadget : IGadget {
    public List<string> GetInputWireNames() => ["left", "right"];
    public List<string> GetOutputWireNames() => ["is_greater_equal_than"];

    public GadgetInstance ApplyGadget(IReadOnlyList<Wire> inputWires, string namePrefix) {
        if (inputWires.Count != 2) {
            throw new ArgumentException("Unexpected element count", nameof(inputWires));
        }

        GadgetIncompleteCircuitBoard circuitBoard = new();

        Wire isLessThanWire;
        {
            GadgetInstance ins = new FieldLessThanGadget().ApplyGadget([inputWires[0], inputWires[1]], $"{namePrefix}_[less_than]");
            ins.Save(circuitBoard);
            isLessThanWire = ins.OutputWires[0];
        }

        Wire outputWire;
        {
            GadgetInstance ins = new BoolNotGadget().ApplyGadget([isLessThanWire], $"{namePrefix}_[not]");
            ins.Save(circuitBoard);
            outputWire = ins.OutputWires[0];
        }

        return GadgetIncompleteCircuitBoardHelper.NewGadgetInstanceFromGadgetIncompleteCircuitBoard([outputWire], circuitBoard);
    }
}
