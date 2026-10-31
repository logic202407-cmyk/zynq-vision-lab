# Safety-supervisor corrections

The first CRC implementation failed GCC signedness checks; explicit bit-step
branches corrected it without suppressing warnings. A stale fake board clock
then exposed the importance of preserving UART-arrival versus evaluation time:
normal fixtures now advance both while stale tests deliberately separate them.
The strict P0 parser caught an incompatible status extension; S1STAT is separate
and the old read-only parser remains strict. Hardware registers, PLL/RNG entropy
and real stop timing are model-tested only and cannot be labelled board verified.
The former verified bridge/firmware and all board state are untouched this round.
