# ChipWhisperer TVLA

ChipWhisperer TVLA is a python project that aims to make running
Test Vector Leakage Assessments (TVLA) easier, a testing methodology
for evaluating the resistance of a microcontroller to side-channel power leakage.

`cwtvla` focuses on AES (128 and 256) and supports the following TVLA tests:

* Non-specific tests
    * Fixed vs. Random Text
    * Semifixed vs. Random Text
    * Fixed vs. Random Key

* Specific tests
    * Random Vs. Random Text

`cwtvla` supports arbitrary leakage points for Random Vs. Random evaluation
for both value/distance of bits/bytes. 

## Documentation

Make sure sphinx is installed and navigate to `docs/`, then run `make html`.

## Basic Usage

### Getting Data

```python
ktp = cwtvla.FixedVRandomText()
key, text = ktp.next_group_A()
waveA = capture_trace(scope, target, text, key)
key, text = ktp.next_group_B()
waveB = capture_trace(scope, target, text, key)
```

For acquiring Random Vs. Random data, use the Fixed vs. Random Text group B
and save both the trace waves and plaintext. A single set of Random Vs. Random
data can be used for all Random Vs. Random analysis.

You can store your trace data however you like, but analysis functions expect numpy arrays.

### Analysis

Once you have your data, you can also use `cwtvla` for analysis of your data.
For non-specific tests, a simple:

```python
t_val = cwtvla.t_test(group1, group2)
fail_points = cwtvla.check_t_test(t_val)
if len(fail_points) > 0:
    print("Test failed at: {}".format(fail_points))
```

will suffice.

Random Vs. Random analysis is more complicated and requires you to create a function
describing where you want to evaluate leakage at. Some basic leakage models,
such as the SBox output and the distance between the input and output of a round,
are provided. You can also modify which rounds, bytes, and bits/vals are tested.

### ChipWhisperer Integration

`cwtvla` also has a module to take care of setup and integrate with different ChipWhisperer
scopes and targets. 

## Examples

A basic showcase is available in the `examples/` directory.