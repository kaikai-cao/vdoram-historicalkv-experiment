# VDORAM 论文关键原文摘录（带页码）

来源：`paper/vdoram-ndss2026.pdf`（NDSS 2026 官方 PDF，`https://www.ndss-symposium.org/wp-content/uploads/2026-s16-paper.pdf`，本地 1,167,622 bytes）。
页码为 PDF 页码（1-indexed），与论文印刷页码一致（p4 印刷页码=4）。摘录为机器提取，逐字保留；标注用于审计引用。


## PDF p4

```text
Dora, based on the proposed concept of ZKBag. By introduc-
ing disjunctive zero-knowledge [6], [32], [53], [54], [55], their
approach further enhances efficiency by allowing introducing
additional instructions to the processor circuit at no extra cost.
Saint Guilhem et al. proposed the construction of verifiable
RAM based on public-coin ZKPs [19].
Distributed Oblivious RAMs. Differing from vRAMs that
focus on public verifiability, distributed oblivious random ac-
cess machines (DORAMs) [73] represent a significant area in a
multi-party setting, which is also known as RAM-MPC. Here,
each party holds a portion of the secret and they work together
to execute the RAM without relying on a trusted entity to
hold all the secrets. Marcel Keller introduced a practical
implementation of an oblivious machine within the arithmetic
black-box model [48], leveraging SPDZ [18], an MPC protocol
that offers active security. Subsequently, Keller et al. devised
a garbled-circuit-based RAM with active security [51], which
minimizes the number of broadcast rounds between memory
accesses. Ji et al. [44] concentrated on constructing a RAM ca-
pable of private function evaluation. Falk et al. have introduced
a 3-party distributed RAM-MPC framework [23] that boasts
logarithmic overhead and is resilient to malicious adversaries.
In addition, Hamlin et al. proposed their first construction of
FHE-based ORAM [36], [35].
Numerous efforts have been directed toward implementing
RAM with a focus on either public verifiability or distributed
obliviousness. However, research remains sparse in scenarios
where both properties are of significance. The existence of
a VDORAM, verifiable distributed oblivious random access
machine, is a question that has not been comprehensively
addressed.
III. MODEL AND PRELIMINARIES
This section begins with an introduction to our model,
including system roles, threat model, and the essential prop-
erties of our VDORAM. Subsequently, we will introduce
several underlying building blocks, including collaborative
zkSNARKs, multi-party computation, arithmetic circuits, and
RAM runtimes.
A. System and Threat Model
Our VDORAM is designed to create a distributed oblivious
vRAM that enables a group of provers to collaboratively
execute a given program using their individual inputs. Upon
completion, the provers collectively convince non-interactive
verifiers, attesting to the integrity of the outputs.
The following are the system roles along with the associated
threat model.
• Provers. Provers are responsible for operating the VDO-
RAM runtime, supplying input data, and generating zero-
knowledge proofs for verifiers. Correctness: The group of
provers is considered malicious to verifiers: it is assumed
that 0 provers will act honestly, i.e., all provers are
eager to collude to compromise the correctness of results
for their personal gains. Privacy: Provers do not seek
privacy if they are able to compromise correctness. If it’s
nearly impossible to compromise correctness, the provers
attempt to protect their secrets from being exposed: each
prover is considered as a polynomial time adversary,
curious to obtain confidential information from other
provers, where at least t (e.g., t = 1) provers will act
honestly to protect their secrets from being exposed.
• Non-interactive verifiers. Similar to participants in tradi-
tional NIZK contexts, verifiers in our system can be any
entity that assesses the validity of the proofs provided by
the provers. These verifiers are not entrusted with any
confidential or sensitive data, except for that which can
be inferred from the public outputs.
• Trusted initializer. They generate the public parameters
for collaborative zkSNARKs, as well as precomputed data
such as beaver triples for MPC.
• Program vendors. They publicly provide programs to be
executed within the VDORAM runtime. These programs
are audited and are trusted not to embed additional
information in their outputs.
Our VDORAM necessitates the following properties.
• Completeness. Honest provers can complete the compu-
tation process and generate a valid proof.
• Knowledge soundness. Even in the event of collusion
among all provers to produce a false proof, the probability
of successfully passing the verification process remains
negligible.
• Succinctness. The verification time should be significantly
less than the computation and proof generation time.
• Zero-knowledge. Verifiers should not acquire any con-
fidential information from any prover, except for those
derived from public output.
• Distributed obliviousness. Each prover should not acquire
any confidential information from any other prover, ex-
cept for those derived from public output and private
output meant to be revealed among provers.
The provers firstly utilize an MPC protocol for computing
all necessary intermediate values as secret shares. Subse-
quently, they apply collaborative zkSNARKs [66] to gen-
erate a publicly verifiable proof using these secret shares
as witnesses. We adopt a dishonest-majority MPC protocol
supporting mixed boolean logic and arithmetic computations
over a finite field Fp and the ring Z2n . Below explains the
considerations:
• Integrating zkSNARKs. Our threat model assumes that the
entire set of provers may be malicious. While a mali-
ciously secure dishonest-majority MPC protocol guaran-
tees the privacy of computations as long as at least t
provers behave honestly, we additionally require public
verifiability. This is achieved by enabling independent
verification of the computations’ correctness through col-
laborative zkSNARKs. This approach ensures that even
if all provers collude, a public verifier can still verify the
integrity of the computation.
• Mixed computations. Collaborative zkSNARKs typically
operate on statements expressed as arithmetic operations
over a finite field Fp. However, unlike a standalone MPC
4
```


## PDF p5

```text
application, when MPC is used to support zkSNARKs, it
must compute auxiliary data in addition to the primary
computational result. This necessitates supporting compu-
tations in both the boolean domain and the ring Z2n . This
mixed-domain computation is essential for generating the
necessary inputs for the zkSNARK proof system.
B. Preliminaries
1) Collaborative zkSNARKs: A zero-knowledge Succinct
Non-interactive ARgument of Knowledge (zkSNARK) is a
cryptographic protocol in which a prover P convinces a
verifier V that a pair (x, w) ∈ R without revealing w. Here, x
is referred to as the instance or public input, and w serves
as the private input, also known as the witness. Initially,
zkSNARKs [34], [65], [28], [15] were designed for a single
prover P. Then, Ozdemir et al. expanded this scheme to a
multi-prover scenario, introducing the concept of collabora-
tive zkSNARKs [66]. This concept were further improved
in [62], [2], [40]. In a collaborative zkSNARK, m provers
P0, P1, . . . , Pm−1 each hold a witness wi and they collectively
aim to convince the verifier V that (x, w0, w1, . . . , wm−1) ∈
R. This protocol contains the following algorithms:
• Setup(1λ, R) → pp: Produces the public parameters pp.
• Prove(pp, x, w0, w1, ..., wm−1) → π: Generates a proof
π if (x, w0, w1, ..., wm−1) ∈ R in MPC; aborts otherwise.
• Verify(pp, x, π) → {0, 1}: Validates the proof π.
An (m, t) collaborative zkSNARK has properties as follows:
• Completeness: Honest provers generate a valid proof
when they have valid witnesses such that (x, w0, w1, ...,
wm−1) ∈ R.
• Knowledge soundness: Provers without knowledge of
valid witnesses cannot produce a valid proof.
• t-zero-knowledge: If less than t provers collude, provers
and verifiers cannot gain any information about witnesses
w0, w1, ..., wm−1 (excluding wi for prover Pi).
• Succinctness: Both the proof size and the verification time
are o(|R|), where |R| denotes the size of relation R.
2) Multi-Party Computation: A multi-party computation
(MPC) protocol [18], [10], [49] involves m parties, each
performing computations to determine the outcome y ←
f (x0, x1, . . . , xm−1), where f is a function defined as f :
X m → Y . In this protocol, each party i possesses an input
xi ∈ X. An MPC protocol is considered secure if it reveals
no additional information beyond that which is implicit in
the output y. As long as no more than t parties collude, the
protocol maintains its security.
In particular, our research focuses exclusively on dishonest-
majority MPC protocols. In dishonest-majority MPC proto-
cols, where typically t = m − 1, additive secret sharing is
utilized. In this scheme, a secret value a is distributed among
the parties as a0, a1, . . . , am−1, each party holding a share
such that the sum of all shares equals a. We use the notation
[a] to denote the secret shares of the value a held by each
party. To compute addition r ← a + b, each party computes
their share as [r] ← [a] + [b] within ring or fields. To compute
multiplication r ← a · b, parties consume a pre-shared Beaver
triple ([α], [β], [γ]) such that α · β = γ. They broadcast and
reveal δ and ϵ where [δ] = [a] − [α] and [ϵ] = [b] − [β]. The
final share is computed as [r] ← [γ] + δ · [β] + ϵ · [α] + δ · ϵ.
To facilitate complex operations beyond simple arithmetic,
particularly those requiring bit-level manipulation within a
prime field setting, we additionally utilize two techniques
in mixed MPC: doubly-authenticated bit (daBit) [70] and
extended doubly-authenticated bits (edaBit) [22]. A daBit
consists of a random bit r ∈ [0, 1] that is secret-shared among
parties in both an arithmetic domain [r]p ∈ Fp and a Boolean
domain [r]2 ∈ [0, 1], useful to convert a Boolean secret
share into an arithmetic share by utlizing B2Ap protocol [1].
Similarly, an edaBit provide shares of a random value r ∈ Fp
in an arithmetic domain [r]p ∈ Fp, along with shares of its
individual bits [r]i ∈ [0, 1] (i ∈ [0, l), where l denotes the bit
length of p) in a Boolean domain.
Publicly verifiable MPC, also known as publicly auditable
MPC, is usually constructed by committing values to a public
bulletin-board and constructing an NIZK proof checking the
transcript [5], [7], [8], [69], [47]. Alternatively, Ozdemir et al.
[66] proposed a novel publicly verifiable MPC construction
from their proposed multi-prover ZKP, verifying statements
in R1CS. We favor this latter approach due to its capability
to enable the construction of efficient proofs focused on only
checking the integrity of RAM states, as opposed to validating
the entire sequence of computations leading to those states.
3) Arithmetic Circuit: An arithmetic circuit [13], [67], [14],
[9] is a directed acyclic graph (DAG) consisting of gates
and wires, commonly used in both MPC and zkSNARKs
programming. Each wire carries a value within a finite field
Fp; additionally, they may also operate within a ring Z2n
for MPC, which we will utilize later. Gates in the circuit
take in wires as inputs and generate output wires based on
the operation they perform, either addition or multiplication.
Moreover, arithmetic circuits can be easily converted to rank-1
constraint system (R1CS).
4) Rank-1 Constraint System: An R1CS is a set of con-
straints, where each constraint is a triplet of vectors a, b, c
satisfying (a·s)·(b·s)−c·s = 0 in Fp. Here, s is the solution
vector, which contains instances (all constant or public inputs)
and witnesses (all private inputs and all intermediate values).
This structure forces any complex computation to be flattened
into a series of additions and multiplications checks, which is
typically done by a ZKP front-end.
5) Verifiable Random Access Machine: We adopt the defi-
nition from [3] and [30]. A random access machine runtime is
defined as a program receiving an input tuple (I, E, in), where
I denotes a code image vector of instructions, E represents the
entry point, and in denotes input data.
A register-based RAM maintains a state s, represented by
the tuple (pc, R, M, halt), where pc denotes the program
counter, referring the location of an instruction in the code
image vector I, R represents a set of registers that hold
values, M denotes the memory state, and halt is a public bit
indicating whether the machine has reached its termination.
The RAM runtime simulates the semantics of each instruction
5
```


## PDF p8

```text
return b = 1 if a = 0, otherwise return 0. This can be
implemented using the inversion-or-zero primitive: let inv
represent the inversion-or-zero result of a, and then return
b ← 1 − a · inv.
• Equality check. To avoid conditionally branching intro-
duced in [19], we migrate the implementation by [41],
which begins by subtracting the two elements and subse-
quently zero-testing the difference.
• Less-than comparison. Given two elements a and b, return
a bit c indicating whether a < b. It is constructed
from initially performing fully bit-decomposition of the
two elements and subsequently comparing them utilizing
boolean operations. The bit sequences and intermediate
results act as auxiliary witnesses to prove the correctness.
Despite its higher complexity compared to a pure MPC
implementation [64], the increased overhead is justified
by the proof requirements.
With CompatCircuit, it becomes straightforward to con-
struct the execution circuit for VDORAM. We refer to the full
version of our paper [68] for the protocols of all VDORAM
circuits. However, it remains to be determined whether the
memory fetch, trace sort, and trace verification circuits can
achieve efficient construction in obliviousness. This will be
the focus of our investigation in the following subsection.
C. Memory Management: Balancing Oblivious Computation
Overheads with Proof Generation Complexity
Oblivious ArrayInstruction Execution
Push
Oblivious Array
Order by
Oblivious Sort Permutation Proof
Adjacent Check
(addr, t , op, val)
SELECT val WHERE 
addr = addrquery
ORDER BY t  DESC
LIMIT 1
(addr, t )
M M '
Fig. 4. Memory management scheme of VDORAM.
As shown in Figure 4, we construct a multi-prover memory
management scheme based on [26]. The main procedures are
as below: 1) During each instruction execution, a memory
access tuple m = (addr, t, op, val) is generated and saved
to the oblivious array M, where t refers to a monotonically
increasing timestamp and op indicates if the memory access is
a load or a store instruction. Note that in our VDORAM, we
also want to hide whether the instruction relates to memory
access or not, and therefore, if not, we specify the memory
address addr with the maximum value, p − 1 in Fp. 2) During
each memory fetch, the stored memory value might be obliv-
iously fetched with an address filter, and if there are multiple
values, select the one with the largest t, which means the
most recent value that corresponds to the address. 3) After
the machine halts, the prover needs to prove the correctness
of T memory accesses. First, sort the vector M ′ from M so
that M ′ is ordered firstly by memory address addr, then by
time t. Then, a permutation check enforces that no values are
altered during the sorting process. Following this, a memory
consistency check scans the sorted vector, and for each pair of
adjacent lines i and i + 1, the following condition from [26]
holds, ensuring that for each load operation, the value retrieved
matches the most recently stored value at that address:
((addri < addri+1) ∨ ((addri = addri+1) ∧ (ti < ti+1)))
∧((addri ̸= addri+1) ∨ (vali = vali+1) ∨ (opi+1 = store))
∧((addri = addri+1) ∨ (opi+1 = store)) (1)
Now, we will discuss detailed construction in a multi-prover
setting. By incorporating CompatCircuit, we can program
this verification statement within CompatCircuit, facilitating
the automatic construction of MPC protocol to compute and
provide the necessary secret-shared auxiliary inputs for collab-
orative zkSNARKs. However, there are more considerations
beyond a naive combination.
Oblivious array. Single-prover vRAMs employ a plaintext
array to manage memory data. Transitioning to a multi-prover
context, we can replace the plaintext array with an oblivious
storage element similar to those utilized in MPC-based DO-
RAM schemes. For instance, a 2-party Circuit ORAM [73]
used by [48], or a 3-party random access memory [23].
In VDORAM, the oblivious storage is required to facilitate
the confidential insertion or overwriting of new memory
values at a specified address, retrieving the latest memory
value corresponding to that address, and supporting memory
consistency checks. We demonstrate the ideal functionality
needed by our VDORAM in Figure 5, where the auxiliary
data aux = (t, op). Note that, our VDORAM requires a unique
FHistoricalKV.Export() functionality, which is not needed for a
regular DORAM.
Functionality FHistoricalKV
Parameters. Memory size n that restricts the address
addr ∈ [0, n − 1].
Functionality. FHistoricalKV.Add(addr, val, aux): add or
update memory value val associated with address addr.
FHistoricalKV.Query(addr): return the latest memory value
val associated with address addr.
FHistoricalKV.Export(): return an oblivious array containing
all (addr, val, aux) tuples, including those being overwrit-
ten.
Fig. 5. Ideal functionality for the memory storage in VDORAM.
The implementation of FHistoricalKV should maintain oblivi-
ousness, meaning provers must not acquire any supplementary
information about any given addr. For instance, provers should
even remain unaware of the number of times an unknown
memory address has been accessed, as disclosing such infor-
mation could compromise security. A conventional DORAM
scheme commences by initializing the storage and then simu-
lating memory accesses online, overwriting the storage if the
address already contains a value. This approach of discarding
outdated data is appropriate for traditional DORAM imple-
mentations, which do not require public verifiability since
integrity can be evaluated based on the security guaranteed
by maliciously secure MPC. To enable public verifiability, it
8
```


## PDF p9

```text
is critical to retain all historical memory accesses from which
the proof is derived.
One initial approach involves implementing FHistoricalKV by
adapting the oblivious storage employed in DORAM, along
with an append-only oblivious array to store (addr, val, aux)
for each FHistoricalKV.Add() access. Nevertheless, despite the
requirement for provers to allocate approximately double the
space for two oblivious structures, existing efficient DORAM
schemes support an insubstantial number of parties. This
does not align with our VDORAM aims, which seek to
accommodate an arbitrary number of provers beyond just two
or three. Consequently, we have implemented this functionality
in MPC using only one linearly-scanned oblivious array, with
an additional requirement that the timestamp t contained in
aux must exhibit a monotonically increasing pattern every time
FHistoricalKV.Add() is invoked. Protocol ΠHistoricalKV:
• Upon receiving ΠHistoricalKV.Add(addr, val, aux), insert
the tuple to the end of array M.
• Upon receiving ΠHistoricalKV.Query(addr), for
each memory tuple mi in array M, compute
bi ← EqualityCheck(addr, addri) ∈ {0, 1}. Then,
set bi ← 0 if there exists a larger bj = 1 where j > i.
Finally, return P|M | i=1 bi · vali.
• Upon receiving ΠHistoricalKV.Export(), return the array M.
Oblivious sort. Migrating vRAM into multi-prover setting,
the vector M is no longer in plaintext. We must sort the
vector in a manner that conceals its values, This is a problem
well-studied in the literature [4] [45]. We opted for Bitonic
mergesort; however, adapting this algorithm for VDORAM
necessitates modifications. Initially, the scheme from [26]
requires an ordered vector M ′ primarily by memory address
addr, and secondly by time t. Typically, this is achieved by
performing a stable sorting by time, followed by a second
sorting by address. However, since Bitonic mergesort is in-
herently unstable, we introduce a complex comparer, slightly
increasing overhead by adding an additional equality check:
m1 < m2 ⇐⇒ (addr1 < addr2) ∨ ((addr1 = addr2) ∧ (t1 <
t2)). Moreover, Bitonic mergesort requires the size of vector
|M | to be a power of 2. Hence, we must pad the vector before
sorting and subsequently remove the padded elements post-
sorting without plaintext access. We append the vector with
padding item mpad = (p − 1, p − 1, p − 1, p − 1), where
p − 1 ∈ Fp. These padding items, being greater than any
real memory access tuples, allow provers to safely remove
them from the end of the vector without exposing the actual
contents.
Different consideration in memory check performance.
In single-prover vRAM, memory check schemes such as in
[19] are generally considered more efficient than [26], featur-
ing reduced proof generation time. However, the efficiency and
associated overhead of a scheme differ significantly within our
VDORAM context as opposed to a single-prover vRAM. In
a conventional single-prover scenario, the computation stage
where plaintext computations occur is essentially negligible
and considered almost free in comparison to the complexity of
the circuit verifying the statements. In [26], the memory access
vector M of size T is sorted, accompanied by a permutation
proof and T −1 less-than checks on adjacent timestamp values.
Conversely, [19] expands the vector to size 2T , implementing
a permutation proof and T − 1 difference checks on adjacent
timestamp values. In the single-prover scenario, [19] offers
enhanced efficiency over [26], as sorting the values in plaintext
is inexpensive, irrespective of whether the vector size is T or
2T . However, operations such as the heavyweight less-than
or lightweight difference checks must be represented within
an arithmetic circuit, and the size of this circuit constitutes
the primary overhead in proof generation. In contrast, multi-
prover scenarios replace all plaintext values with secret shares
in MPC, making latency a crucial factor. Computation stage
is no longer free in terms of cost: an MPC sorting network
incurs substantial overhead due to the extensive communica-
tion required. We will further demonstrate this overhead in
our evaluation, Section V. Given these considerations, for our
multi-prover implementation, we support the adoption of the
memory checking protocol proposed in [26] in contrast to [19],
due to its relative simplicity and reduced computational and
communicational demands in multi-prover contexts.
D. Protocol Specification
Putting it all together, we construct our VDORAM, provid-
ing the full protocol below.
Protocol ΠVDORAM
Input: An instruction vector I with entrypoint E is
publicly provided. m provers exclusively and privately
holds N inputs ini which corresponds to the i-th input
the machine asks for.
Protocol:
1) Trusted setup: the trusted initializer generates public
parameters for collaborative zkSNARKs. Provers
generate sufficient beaver triples, edaBit, and daBit
for multi-party computation.
2) Each prover construct and broadcast secret shares of
his/her input [ini] to one other provers.
3) Set public timestamp t ← 0. Initialize all registers
[Rj ] ← 0. Set the program counter to the entrypoint
[pc] ← E. Initialize memory access vector [M] ←
().
4) Provers run instruction fetch protocol. Given I and
[pc] as input, provers fetches the next instruction [I]
as well as the instruction type indicator opmasked ∈
{input, output, secret}. This protocol does not
reveal information about an non-IO instruction.
5) If opmasked = input, provers assign the input value
[in] ← [ini] where i denotes the count of previously
provided inputs. Otherwise, provers publicly set it
to 0.
6) If t ≥ 1, provers run memory fetch protocol. Given
[I], [Raddr], and [M], provers fetches the latest
memory value [val]. Private output [val] would be a
secret-shared 0 if the instruction is not related with
9
```


## PDF p10

```text
memory access or the address has never been stored
with a value. In particular, if t = 0, provers publicly
sets [val] ← 0.
7) Provers run instruction execution protocol. Given
[I], [val], t, [pc], [in], and all registers [Rj ], the
protocol returns updated register values as [pc]′ and
[Rj ]′. A memory access trace [m] = ([addr], t, [op],
[val]) is also produced. The protocol also returns
the output value [out] if the operation type matches;
otherwise, it’s 0. Provers accordingly updates values
and insert [m] to vector [M].
8) If opmasked ̸= halt, increase t ← t + 1 and go to
the instruction fetch protocol.
9) Provers run trace sort protocol to pad and sort the
memory access vector [M ]. Get sorted vector [M ]′.
10) Provers run trace verification protocol with input
[M ] and [M ]′. The verification result is publicly
revealed.
11) For all instruction fetch, instruction execution, and
the final trace verification protocol, provers in-
voke collaborative zkSNARKs, providing all in-
puts, outputs, intermediate results, and auxiliary data
with necessary hash digests, and getting an non-
interactive succinct proof π.
During each round, provers begin by retrieving the next
instruction to be executed through an instruction fetch circuit.
Except for the case of a halt or IO operation, provers get no ex-
tra information about which instruction will be executed next.
Subsequently, regardless of whether the instruction involves a
memory read/write operation, they fetch the memory value for
a specified address from a blind memory trace table using a
memory fetch circuit. Following this, the instruction execution
circuit is utilized to interpret the execution by computing,
updating registers, inserting a new row to the memory trace
table, and interacting with public/private I/O if the instruction
type matches. These three types of circuits are repeatedly
executed upon fetching an instruction, continuing until the
machine reaches a halt state. Upon completion, the trace sort
circuit is run to blindly pad and sort the memory trace table.
This is succeeded by the execution of a trace verification
circuit, which checks the correctness of the entire memory
management process.
E. Performance and Security Analysis
1) Communication overhead of CompatCircuit primitives:
Let l = ⌈log2 p⌉ denote the number of bits in the finite field
Fp. An addition operation does not require communication,
while a multiplication operation requires broadcasting one
revealed element, thus incurring 1 round of communication.
The inversion-or-zero operation necessitates l + 4 rounds of
multiplications: l multiplications to secretly obtain the inverse,
and an additional 4 multiplications for constructing the verifi-
cation statements. A fully bit-decomposition operation incurs
19l + 2 rounds of communications:
• 1 round for exposing c.
• 3l multiplications for an l-bit MPC adder with a plaintext
operand, where each adder requires at most 3l multipli-
cations.
• 6l multiplications: l for multiplying each bit pi with [1 −
q], 5l multiplications for an l-bit MPC adder with a secret
operand.
• 1 round: exposing l boolean values for B2Ap protocol
[1].
• 10l multiplications for computing R1CS witnesses: l for
input range check, l for constructing the field element
from input bits, 8l for ensuring the bits are smaller than
the bit decomposition of field modulus p.
2) Communication overhead in the VDORAM protocol:
In this analysis, we consider l, the number of bits in the
finite field to be a small constant. We additionally denote
T as the total number of iterations, N as the number of
inputs, and I as the length of the instruction vector. It’s
worth noting that our VDORAM protocol employs a read-
write memory model with a full address space, implying that
the memory capacity is virtually unlimited (with a capacity
of p). Therefore, the overhead is not affected by the size of
the memory. The VDORAM protocol incurs the following
communication overheads:
• m · N broadcasts are required for distributing the secret
shares of the inputs.
• O(T · I) rounds of communication occur during T in-
vocations of the instruction fetch protocol. During each
fetch, a linear scan is conducted to determine the next
instruction to be executed, taking O(I) time.
• O(T 2) rounds of communication are required for T
instances of the memory fetch protocol. During each
fetch, a linear scan is carried out to identify the most
recent memory value to be read, taking O(T ) time.
• O(T ) rounds of communication take place for T in-
stances of the instruction execution protocol. The over-
head from the instruction execution circuit can be con-
sidered a constant number of CompatCircuit primitives,
as the number of registers and instruction types are small
constants..
• O(T log2 T ) rounds are needed for the memory
trace sorting protocol. The sorting algorithm requires
O(T log2 T ) comparisons, each necessitating a small
constant number of bit-decomposition primitives.
• O(T ) rounds are required for the memory trace verifica-
tion protocol. This protocol checks each pair of adjacent
lines, which also involves comparisons based on bit-
decomposition.
3) Privacy Disclosure: Our protocol ΠVDORAM is designed
to maintain the confidentiality of sensitive information against
both provers and verifiers. This includes:
• Register values: The contents of the registers are kept
private, including the program counter pc.
• Memory accesses: Information about memory value, ad-
dress, and access type is concealed. The number of
memory accesses equals to the total number of instruction
cycles.
10
```


## PDF p11

```text
Definition IV.1. An (m, t) VDORAM with m provers P = P0, P1, . . . , Pm−1 holding public input inpub and secret shares
of private input inpriv is a RAM (I, E, inpub, inpriv) with the following procedures:
• Setup(1λ, I, E) → pp: Generates zkSNARK parameters.
• Compute(I, E, inpub, inpriv) → outpub, outpriv, s : Computes outpub, outpriv with each machine state si by simulating the
RAM runtime.
• Prove(pp, I, E, inpub, outpub, inpriv, outpriv, s) → π : Generates an execution proof π; aborts if state transitions are
invalid.
• Verify(pp, I, E, inpub, outpub, π) → {0, 1}: Verifies the proof π on whether state transitions are valid.
and with the following properties:
• Completeness: For all (I, E, inpub, inpriv), the following statement holds:
Pr

 VerifyH (pp, I, E, inpub, outpub, π) = 0
 H ← U (λ) pp ← SetupH (1λ, I, E) outpub, outpriv , s ← ComputeH (I, E, inpub, inpriv ) π ← ProveH (pp, I, E, inpub, outpub, inpriv , outpriv , s)   ≤ negl(λ)
• Knowledge soundness: For all (I, E, inpub, inpriv) and for all sets of efficient algorithms P = P ∗ 0 , P ∗ 1 , . . . , P ∗ m−1, there
exists an efficient extractor ExtH,PH such that:
Pr

 (I, E, inpub, outpub, inpriv ,
outpriv , s) ∈ R
 H ← U (λ) pp ← SetupH (1λ, I, E) inpriv , outpub, outpriv , s ←
ExtH,PH (pp, I, E, inpub)

 ≥ Pr

 VerifyH (pp, I, E, inpub, outpub, π) = 1
 H ← U (λ) pp ← SetupH (1λ, I, E) outpub, π ← PH (I, E, inpub)   − negl(λ)
R denotes the collection of valid RAM executions. ExtH,PH denotes Ext has oracle access to H and may re-run the
provers P for multiple times with H re-programmed.
• Succinctness: Proof size and verification time are O(|s|).
• Zero-knowledge: For all efficient A controlling k ≤ t provers P0, P1, . . . , Pk−1, there exists an efficient simulator Sim
such that for all (I, E, inpub, inpriv) and for all efficient distinguishers D, |D0 − D1| ≤ negl(λ) holds, where:
D0 = Pr

 DH[µ](tr) = 1
 H ← U (λ) pp ← SetupH (1λ, I, E) b ∈ {0, 1} = 1 ⇐⇒ (I, E, inpub, outpub, inpriv , outpriv , s) ∈ R (tr, µ) ← SimH (pp, I, E, inpub, outpub, (inpriv , outpriv , s)0,1,...,k−1, b)  
D1 = Pr

 DH (tr) = 1
 H ← U (λ) pp ← SetupH (1λ, I, E) tr ← ViewH A (I, E, inpub, inpriv , outpub, outpriv , s)  
tr is a transcript, ViewH A denotes view of A when provers P interact with I, E, inpub, inpriv, outpub, outpriv, s in Compute
and Prove procedures, µ is a partial function from H such that given an input x, function H[µ] equals µ(x) if x is in
the domain of µ, otherwise equals H(x).
• t-distributed-obliviousness: Conditions are same as Zero-knowledge, except that outpriv is visible among provers. So
the definition is slightly different: update outpub ← outpub ∪ outpriv and outpriv ← ∅.
• Instructions: The specific instruction being executed at
any given time remains hidden, with some I/O exceptions.
However, ΠVDORAM also requires some information to be
publicly available. 1) I/O instruction type. Only input,
output, and halt instructions are revealed to provers.
Provers maintain the protocol, and thereby need to know when
to provide input, when to expect output, and when the machine
has completed its execution. Mitigation: For non-interactive
programs, we can structure the program into three distinct
phases: input, computation, and output. During the input and
output phases, data are simply transferred to and from regis-
ters/memory without any actual processing. This minimizes
the risk of sensitive information being leaked through the
public disclosure of I/O-related instruction types. 2) Total
number of iterations (T ). Like most oblivious RAMs, the
total number of instructions executed by the machine is made
public. This is necessary to halt the machine and facilitate
the proof generation process. Mitigation: Programmers should
11
```


## PDF p14

```text
each of the other m − 1 prover parties, the highest aver-
age bandwidth for an individual prover was 48.63 Mbps.
Although the computation time increases more rapidly than
the zero-knowledge proof generation time when the prover
count increases, computation stage demands more frequent
communication, our implementation still maintains a relatively
reasonable overheads in total, compared with the single-prover
baseline.
Program Examples of VDORAM. To evaluate VDO-
RAM’s applicability, we implemented seven example pro-
grams as shown in Figure 11: bubble sort, sliding window,
set intersection, range query, longest continuous increasing
subsequence (LCIS), Fibonacci, and binary search, highlight-
ing VDORAM’s versatility in handling various computational
patterns.
Bubble
Sort
Sliding
Window
Set
Intersection
Range
Query
LCIS Fibonacci Binary
Search
VDORAM programs
101
102
103
104
Time cost (s)
Preprocess
Compute
ZKP Setup
ZKP Prove
ZKP Verify
Fig. 11. Time costs of VDORAM procedures for programs (2 provers).
Comparison of VDORAM. We compared VDORAM with
prior RAM systems: Jolt [3], SP1 [60], and Wang et al. [74].
Table III highlights the feature differences, emphasizing VDO-
RAM’s unique ability to support both public verifiability and
distributed obliviousness for an arbitrary number of provers.
TABLE III
COMPARISON OF VDORAM WITH PRIOR WORKS
RAM System Number of Parties Public Verifiability Distributed Obliviousness
Jolt [3] 1 prover Yes No
SP1 [60] 1 prover Yes No
Wang et al. [74] 2 parties No Yes
VDORAM (ours) ≥ 1 provers Yes Yes
We also conducted an experimental comparison on set
intersection and binary search programs. Figure 12 shows the
time costs for each system’s main procedures. The results
indicate that VDORAM’s additional overhead is justified by
its multi-prover and proof generation capabilities.
VI. CONCLUSION AND FUTURE WORK
In this research, we have introduced CompatCircuit, a
novel multi-prover ZKP front-end system. CompatCircuit
combines collaborative zkSNARKs with a dishonest-majority
MPC framework, facilitating the creation of multi-prover
ZKP applications. Building upon CompatCircuit, we have
Jolt
(1 Prover)
SP1
(1 Prover)
Wang et al.
(2 Parties)
VDORAM
(2 Provers)
VDORAM
(4 Provers)
Different RAM schemes
10−3
10−1
101
103
Time cost (s)
Compute
ZKP Setup
ZKP Prove
ZKP Verify
Binary Search Set Intersection
Fig. 12. Performance comparison of VDORAM with prior works on set
intersection and binary search programs. In this figure, the compute procedure
of Wang et al. and VDORAM also contains preprocessing time costs. Jolt does
not require ZKP setup procedure.
presented VDORAM, the first publicly verifiable distributed
oblivious RAM. By integrating distributed oblivious archi-
tectures with verifiable RAM, VDORAM achieves a RAM
design that optimizes communication overhead and proof
generation time. We have developed implementations of both
CompatCircuit and VDORAM. Our evaluation with micro-
benchmarks, comparisons, and program examples validates the
feasibility of our approach. Establishing this stronger security
model also brings some limitations that highlight opportunities
for further optimization, shown below.
• Computation and Proof Overhead. Our work establishes a
functional memory model for arbitrary number of provers
by deliberately trading higher computational communica-
tion overhead for a simpler memory consistency proof.
Future work could advance this trade-off by developing
more efficient n-party oblivious data structures to reduce
communication costs. Concurrently, adapting modern ver-
ification techniques like lookup arguments [27], [3] to
the multi-prover setting would further lower the proof
generation overhead.
• Potential Leakage Through I/O Instruction. A minor
information leakage channel exists as provers can observe
the timing of public I/O and halt instructions, for which
we have proposed mitigations in Section IV-E3. Future
work could explore executing a VM with a blind I/O
operation.
• Trusted Setup Requirement. The protocol relies on
a trusted setup for the underlying collaborative zk-
SNARKs, which is a common requirement for many
zk-SNARK-based systems. Our implementation utilizes
Plonk [28], requiring a universal trusted Setup. Future
research could investigate transparent zk-SNARKs [72],
[16] to eliminate the assumption of the trusted initializer.
14
```

