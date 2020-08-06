import chipwhisperer as cw
import time
from cwtvla.ktp import FixedVRandomText, FixedVRandomKey, SemiFixedVRandomText, verify_AES
from cwtvla.tvla_cw import do_tvla, check_t_test, create_projects, t_test
import matplotlib.pyplot as plt
from tqdm import trange

def setup_device(name):
    scope = cw.scope()
    if name == "CW305":
        scope.gain.db = 25
        scope.adc.samples = 129
        scope.adc.offset = 0
        scope.adc.basic_mode = "rising_edge"
        scope.clock.clkgen_freq = 7370000
        scope.clock.adc_src = "extclk_x4"
        scope.trigger.triggers = "tio4"
        scope.io.tio1 = "serial_rx"
        scope.io.tio2 = "serial_tx"
        scope.io.hs2 = "disabled"
        target = cw.target(scope, cw.targets.CW305, bsfile="cw305_top.bit", force=False)
        target.vccint_set(1.0)
        # we only need PLL1:
        target.pll.pll_enable_set(True)
        target.pll.pll_outenable_set(False, 0)
        target.pll.pll_outenable_set(True, 1)
        target.pll.pll_outenable_set(False, 2)

        # run at 10 MHz:
        target.pll.pll_outfreq_set(10E6, 1)

        # 1ms is plenty of idling time
        target.clkusbautooff = True
        target.clksleeptime = 1
    else:
        target = cw.target(scope)
        scope.default_setup()
        scope.adc.samples = 24400
    if name == "XMEGA":
        cw.program_target(scope, cw.programmers.XMEGAProgrammer, "AES-xmega.hex")
    elif name == "STM32F3":
        cw.program_target(scope, cw.programmers.STM32FProgrammer, "AES.hex")
    elif name == "STM32F3-mbed":
        cw.program_target(scope, cw.programmers.STM32FProgrammer, "AES-mbed.hex")
    elif name == "K82F":
        scope.adc.samples=3500
    elif name == "STM32F4":
        cw.program_target(scope, cw.programmers.STM32FProgrammer, "AES-f4.hex")
        scope.adc.samples=5000

    return scope,target

def perform_test(platform, tvla_obj, key_len=16, plot=False, N=1000):
    scope,target = setup_device(platform)

    t_val = do_tvla(scope, target, tvla_obj, N, key_len)

    fail_points = check_t_test(t_val)
    if len(fail_points) > 0:
        print("Test failed at points {}".format(fail_points))
    else:
        print("Passed test")

    if plot:
        plt.plot(t_val[0])
        plt.plot(t_val[1])
        plt.show()

    scope.dis()
    target.dis()

# random v random tests:

# 128 bits of sbox outputs
# 128 bits of round outputs
# XOR of round input and round output (128bits)
# SBox outputs (first 2 bytes, 2x256 values)
# Round outputs
# XOR of round input and output
from scipy.stats import ttest_ind

def t_test_np(group1, group2):
    trace_len = len(group1[0])
    group1_len = len(group1) // 2
    group2_len = len(group2) // 2
    t = np.zeros([2, trace_len], dtype='float64')
    #print("-------------")
    #print(ttest_ind(group1[:group1_len], group2[:group2_len], axis=0, equal_var=False)[0])
    #print("-------------")
    #t[0] = ttest_ind(group1[:group])
    t[0] = ttest_ind(group1[:group1_len], group2[:group2_len], axis=0, equal_var=False)[0]
    t[1] = ttest_ind(group1[group1_len:], group2[group2_len:], axis=0, equal_var=False)[0]
    #for i in range(trace_len):
        #t[0][i] = ttest_ind(group1[:group1_len, i], group2[:group2_len, i], equal_var=False)[0]
        #t[1][i] = ttest_ind(group1[group1_len:, i], group2[group1_len:, i], equal_var=False)[0]

    #print("-------------")
    #print(t[0])
    #print("-------------")
    return t

import numpy as np
def random_v_random_test(platform, plot=True, key_len=16, N=1000):
    scope,target = setup_device(platform)
    ktp = FixedVRandomText(key_len)
    waves = np.zeros((2*N, scope.adc.samples), dtype='float64')
    textins = np.zeros((2*N, 16), dtype='uint8')
    for i in range(2*N):
        key, text = ktp.next_group_B()
        trace = cw.capture_trace(scope, target, text, key)
        while trace is None:
            trace = cw.capture_trace(scope, target, text, key)

        if not verify_AES(text, key, trace.textout):
            raise ValueError("Encryption failed")
        #project.traces.append(trace)
        waves[i, :] = trace.wave
        textins[i, :] = np.array(text)

    print(scope.adc.trig_count)

    # now need to separate based on selection function
    def sbox_selection_function(text, round, byte, bit):
        cipher = ktp._dev_cipher
        state = list(text)
        cipher._add_round_key(state, 0)

        for round in range(1, round):
            cipher._sub_bytes(state)
            cipher._shift_rows(state)
            cipher._mix_columns(state, False)
            cipher._add_round_key(state, round)

        cipher._sub_bytes(state)
        return state[byte] & (1 << bit)

    def roundout_selection_function(text, round, byte, bit):
        cipher = ktp._dev_cipher
        state = list(text)
        cipher._add_round_key(state, 0)

        for round in range(1, round):
            cipher._sub_bytes(state)
            cipher._shift_rows(state)
            cipher._mix_columns(state, False)
            cipher._add_round_key(state, round)

        return state[byte] & (1 << bit)

    def roundinout_selection_function(text, round, byte, bit):
        cipher = ktp._dev_cipher
        state = list(text)
        cipher._add_round_key(state, 0)

        for round in range(1, round):
            rin = list(state)
            cipher._sub_bytes(state)
            cipher._shift_rows(state)
            cipher._mix_columns(state, False)
            cipher._add_round_key(state, round)

        return (state[byte] ^ rin[byte]) & (1 << bit)

    # doing it this way to make it easier to change to different selection function with same data
    for round in trange(2, 8):
        for byte in range(8):
            for bit in range(1):
                truth_array = np.array([roundinout_selection_function(textins[i], round, byte, bit) for i in range(2*N)])
                group1 = waves[truth_array != 0]
                group2 = waves[truth_array == 0]
                t_val = t_test_np(group1, group2)

                fail_points = check_t_test(t_val)
                if len(fail_points) > 0:
                    print("Test failed at points {}".format(fail_points))
                else:
                    print("Passed test")

                if plot:
                    plt.cla()
                    plt.plot(t_val[0])
                    plt.plot(t_val[1])
                    plt.draw()
                    plt.pause(0.00001)


    scope.dis()
    target.dis()

random_v_random_test("STM32F3-mbed", N=1000)
#def perform_test(platform, tvla_obj, key_len=16, plot=False, N=1000):
#perform_test("XMEGA", SemiFixedVRandomText, plot=True)
#perform_test("XMEGA", FixedVRandomKey, plot=True)
#perform_test("XMEGA", FixedVRandomText, plot=True)

#perform_test("STM32F3", SemiFixedVRandomText, plot=True)
#perform_test("STM32F3", FixedVRandomKey, plot=True)
#perform_test("STM32F3", FixedVRandomText, plot=True, N=50)

#perform_test("STM32F3", SemiFixedVRandomText, plot=True)
#perform_test("STM32F3", FixedVRandomKey, plot=True)
#perform_test("STM32F3", FixedVRandomText, plot=True)

#perform_test("STM32F4", SemiFixedVRandomText, plot=True)
#perform_test("STM32F4", FixedVRandomKey, plot=True)
#perform_test("STM32F4", FixedVRandomText, plot=True)

#perform_test("CW305", SemiFixedVRandomText, plot=True)
#perform_test("CW305", FixedVRandomKey, plot=True)
#perform_test("CW305", FixedVRandomText, True)

#perform_test("K82F", SemiFixedVRandomText, 32, True)
#perform_test("K82F", FixedVRandomKey, 32, True)
#perform_test("K82F", FixedVRandomText, 32, True)