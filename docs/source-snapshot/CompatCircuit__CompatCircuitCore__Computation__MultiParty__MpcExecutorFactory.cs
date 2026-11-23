// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/CompatCircuitCore/Computation/MultiParty/MpcExecutorFactory.cs
// BLOB SHA: 07165e08d153e841a903d35c05aa99659e66e20e

﻿using HuayiQi.CompatCircuitCore.Computation.MultiParty.SharedStorages;
using HuayiQi.CompatCircuitCore.MultiPartyComputationPrimitives.BeaverTriples;
using HuayiQi.CompatCircuitCore.MultiPartyComputationPrimitives.DaBitPrioPlus;
using HuayiQi.CompatCircuitCore.MultiPartyComputationPrimitives.EdaBitsKai;

namespace HuayiQi.CompatCircuitCore.Computation.MultiParty;
public class MpcExecutorFactory : IMpcExecutorFactory {
    private IMpcSharedStorageSessionManager MpcSharedStorageSessionManager { get; }
    private IMpcSharedStorageFactory MpcSharedStorageFactory { get; }

    private IMpcSharedStorage? _prevMpcShareStorage = null;
    private MpcExecutor? _prevMpcExecutor = null;
    public MpcExecutorConfig MpcExecutorConfig { get; }
    public IEnumerator<FieldBeaverTripleShare> FieldBeaverTripleShareEnumerator { get; }
    public IEnumerator<BoolBeaverTripleShare> BoolBeaverTripleShareEnumerator { get; }
    public IEnumerator<EdaBitsKaiShare> EdaBitsKaiShareEnumerator { get; }
    public IEnumerator<DaBitPrioPlusShare> DaBitPrioPlusShareEnumerator { get; }

    public int PartyCount => this.MpcExecutorConfig.PartyCount;
    public int MyID => this.MpcExecutorConfig.MyID;

    public int NextSessionID { get; private set; } = 0;

    public MpcExecutorFactory(
        MpcExecutorConfig mpcExecutorConfig,
        IMpcSharedStorageSessionManager mpcSharedStorageSessionManager,
        IMpcSharedStorageFactory mpcSharedStorageFactory,
        IEnumerator<FieldBeaverTripleShare> fieldBeaverTripleShareEnumerator,
        IEnumerator<BoolBeaverTripleShare> boolBeaverTripleShareEnumerator,
        IEnumerator<EdaBitsKaiShare> edaBitsShareEnumerator,
        IEnumerator<DaBitPrioPlusShare> daBitPrioPlusShareEnumerator) {
        this.MpcExecutorConfig = mpcExecutorConfig;
        this.MpcSharedStorageSessionManager = mpcSharedStorageSessionManager;
        this.MpcSharedStorageFactory = mpcSharedStorageFactory;
        this.FieldBeaverTripleShareEnumerator = fieldBeaverTripleShareEnumerator;
        this.BoolBeaverTripleShareEnumerator = boolBeaverTripleShareEnumerator;
        this.EdaBitsKaiShareEnumerator = edaBitsShareEnumerator;
        this.DaBitPrioPlusShareEnumerator = daBitPrioPlusShareEnumerator;
    }

    public MpcExecutor NextExecutor() {
        if (this._prevMpcExecutor is not null && this._prevMpcExecutor.MpcExecutorState != MpcExecutorState.Completed) {
            throw new Exception("Previous MPC Executor has not completed.");
        }

        this._prevMpcShareStorage?.UnregisterSession();

        IMpcSharedStorage newMpcShareStorage = this.MpcSharedStorageFactory.GetSharedStorage(this.MpcSharedStorageSessionManager, this.NextSessionID++, this.PartyCount);

        MpcExecutor newMpcExecutor = new(
            this.MpcExecutorConfig,
            newMpcShareStorage,
            this.FieldBeaverTripleShareEnumerator, // Note: the last MpcExecutor must have ended. Otherwise, these enumerators might be incorrupted.
            this.BoolBeaverTripleShareEnumerator,
            this.EdaBitsKaiShareEnumerator,
            this.DaBitPrioPlusShareEnumerator
        ) { LoggerPrefix = $"MPC{this.MyID}-Session{newMpcShareStorage.SessionID}" };

        this._prevMpcShareStorage = newMpcShareStorage;
        this._prevMpcExecutor = newMpcExecutor;

        return newMpcExecutor;
    }

    IMpcExecutor IMpcExecutorFactory.NextExecutor() => this.NextExecutor();
}
