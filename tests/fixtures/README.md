Drop a real Optidrive E3 .ptb here as `e3_reference.ptb` and switch
tests/test_ptb_modifier.py from its synthetic fixture to this file.

Purpose: confirm the two assumptions the synthetic fixture cannot verify —
the code -> (groupNum, paramNum) convention, and the per-parameter scale
factors (compare <currentValue> against the value shown on the keypad).
