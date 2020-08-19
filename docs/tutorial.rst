.. _tutorial:

########
Tutorial
########

In general, there are two steps for evaluating a device's leakage
using TVLA. The first is capturing data and the second is
evaluating that data. 

***************
Acquiring Data
***************

^^^^^^^^^^^^^^^^^^
Non-Specific Tests
^^^^^^^^^^^^^^^^^^

For non-specific TVLA tests, capture is broken into two campaigns.
During analysis, the data from these two campaigns will be used
in a t-test. It's recommended that data acquisistion be done
simultaneously for these data sets - aka swap back and forth between
campaigns instead of doing them in sequence.

Begin by creating a key text pair object::

    import cwtvla
    ktp = cwtvla.FixedVRandomText(key_len=16)

The dataset for each campaign can be accessed individually::

    key, text = ktp.next_group_A() # fixed key, fixed text for FixedVRandomText
    key, text = ktp.next_group_B() # fixed key, random text for FixedVRandomText

From there, it's as simple as a normal capture campaign. Record the trace wave
data from each campaign and keep them separate. There's no need to record
plaintext, key, or ciphertext, but it's recommended that you validate the 
ciphertext that you get back from the target device every time you 
capture a trace::

    cwtvla.verify_AES(plaintext, key, ciphertext)

If you're using a ChipWhisperer device, a full capture campaign
(minus error checking) might look like::

    import cwtvla
    import chipwhisperer as cw
    import numpy as np
    ktp = cwtvla.FixedVRandomText(key_len=16)

    scope = cw.scope()
    target = cw.scope(target)
    scope.default_setup()
    cw.program_target(scope, cw.programmers.STM32FProgrammer, "fw.hex")

    N = 10000 # capture 10000 traces for each group
    groupA = np.zeros((N, scope.adc.samples), dtype='float64')
    groupB = np.zeros((N, scope.adc.samples), dtype='float64')

    for i in range(N):
        key, text = ktp.next_group_A() # fixed key, fixed text for FixedVRandomText
        trace = cw.capture_trace(scope, target, text, key)
        groupA[i,:] = trace.wave[:]

        key, text = ktp.next_group_B() # fixed key, random text for FixedVRandomText
        trace = cw.capture_trace(scope, target, text, key)
        groupB[i,:] = trace.wave[:]

Adapt the above to your capture setup.

^^^^^^^^^^^^^^^
Specific Tests
^^^^^^^^^^^^^^^

Data acquisistion for specific tests is similar except
only a single campaign is needed. For this data, use 
the group_B key/text pair from the FixedVRandomText ktp
and record both trace wave data and plaintext.::

    import cwtvla
    import chipwhisperer as cw
    import numpy as np
    ktp = cwtvla.FixedVRandomText(key_len=16)

    scope = cw.scope()
    target = cw.scope(target)
    scope.default_setup()
    cw.program_target(scope, cw.programmers.STM32FProgrammer, "fw.hex")

    N = 10000 # capture 10000 traces for each group
    waves = np.zeros((N, scope.adc.samples), dtype='float64')
    textins = np.zeros((N, 16), dtype='uint8')

    for i in range(N):
        key, text = ktp.next_group_B() # fixed key, fixed text for FixedVRandomText
        trace = cw.capture_trace(scope, target, text, key)
        waves[i,:] = trace.wave[:]
        textins[i,:] = np.array(text)[:]

****************
Evaluating Data
****************

:code:`cwtvla` expects numpy arrays in the following formats::

    trace_data = np.array(shape=(num_traces, trace_len), dtype='float64')
    textin_data = np.array(shape=(num_traces, 16), dtype='uint8')

^^^^^^^^^^^^^^^^^^
Non-Specific Tests
^^^^^^^^^^^^^^^^^^

Evaluating data from non-specific tests is simple,
provided your trace data is in numpy arrays::

    t_val = cwtvla.t_test(groupA, groupB)
    fail_points = cwtvla.check_t_test(t_val)
    if len(fail_points) > 0:
        print("Test failed at: {}".format(fail_points))

^^^^^^^^^^^^^^^
Specific Tests
^^^^^^^^^^^^^^^

As a part of the evaluation process for specific tests,
trace data must be separated by the value of intermediates
in the AES state. Two common ways on doing this are via
bit values, and via byte values. :code:`cwtvla` includes
a generic function for building your own separator by both
bit and byte. For example, to separate by the value of the 0th bit, 0th
byte of the second SBox output::

    func = lambda text: cwtvla.leakage_func_bit(text, 0, 0, ktp._dev_cipher, cwtvla.leakage_lookup("subbytes", 2), 0)
    truth_array = np.array([func(textins[i], ktp._cipher_dev) for i in range(len(waves))])
    groupA = waves[truth_array != 0]
    groupB = waves[truth_array == 0]

From there, you can do a t-test as normal::

    t_val = cwtvla.t_test(groupA, groupB)
    fail_points = cwtvla.check_t_test(t_val)
    if len(fail_points) > 0:
        print("Test failed at: {}".format(fail_points))

:code:`cwtvla` has a generic specific evaluation function to automate scanning
over a range of AES rounds, bytes, and bits, as well as some common leakage points
to evaluate::

    eval_rand_v_rand(waves, textins, func=cwtvla.sbox_hw)

By default, :code:`eval_rand_v_rand()` tests over the full leakage search space
(from round 2 to the last round, 16 bytes, 8 bits). You can customize
the search space as follows, attacking rounds 2-4, bytes 5 and 6, bits 2 and 7::

    eval_rand_v_rand(waves, textins, func, round_range=[2,3,4], byte_range=[5,6], bit_range=[2,7])

Here func has the following function prototype::

    func(text: list, byte: uint8, bit: uint8, cipher: AESCipher, rnd: uint8) -> bool

To make it easier to generate leakage functions, you can use the function constructors :code:`construct_leakage_bit`
and :code:`construct_leakage_byte`::

    func = cwtvla.construct_leakage_bit("addroundkey", "subbytes")

***************************
ChipWhisperer Convenience
***************************

:code:`cwtvla`, includes an additional submodule to automate data collection with ChipWhisperer
scopes and targets. To setup and program a scope and target::

    scope, target = setup_device("STM32F3") # STM32F3 TINYAES

You can then either do a full capture run, putting the data in a ChipWhisperer zarr::

    import cwtvla.cw_convenience as conv
    z = conv.capture_all(scope, target, "STM32F3")

Or do tests individually, which return numpy arrays::

    group1, group2 = conv.capture_non_specific(scope, target, cwtvla.FixedVRandomText)
    waves, textins = conv.capture_rand(scope, target)

ChipWhisperer zarr containers have a tree in the following format::

        /
        ├── PLATFORM_A
        |   ├── FixedVRandomKey-KEY_LEN
        |   │   ├── results
        |   │   │   └── tvla (2, scope.adc.samples) float64
        |   │   └── traces
        |   │       ├── group1 (N, scope.adc.samples) float64
        |   │       └── group2 (N, scope.adc.samples) float64
        |   ├── FixedVRandomText-KEY_LEN
        |   │   ├── results
        |   │   │   └── tvla (2, scope.adc.samples) float64
        |   │   └── traces
        |   │       ├── group1 (N, scope.adc.samples) float64
        |   │       └── group2 (N, scope.adc.samples) float64
        |   ├── RandVRand-KEY_LEN
        |   │   └── traces
        |   │       ├── textins (N, 16) uint8
        |   │       └── waves (N, scope.adc.samples) float64
        |   └── SemiFixedVRandomText-KEY_LEN
        |       ├── results
        |       │   └── tvla (2, scope.adc.samples) float64
        |       └── traces
        |           ├── group1 (N, scope.adc.samples) float64
        |           └── group2 (N, scope.adc.samples) float64
        |
        ├── PLATFORM_B
        .
        .
        .

