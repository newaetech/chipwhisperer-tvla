import zarr
import numpy as np
from scipy.stats import ttest_ind 
from tqdm import trange
from .ktp import FixedVRandomText
import matplotlib.pyplot as plt
import tqdm


def leakage_lookup(operation, round):
    opn = 0
    if operation == "subbytes":
        opn = 0
    if operation == "shiftrows":
        opn = 1
    if operation == "mixcolumns":
        opn = 2
    if operation == "addroundkey":
        opn = 3
    if operation is None:
        return 0

    return 2+(opn)+4*(round-1)

def t_test(group1, group2):
    trace_len = len(group1[0])
    group1_len = len(group1) // 2
    group2_len = len(group2) // 2
    t = np.zeros([2, trace_len], dtype='float64')
    t[0] = ttest_ind(group1[:group1_len], group2[:group2_len], axis=0, equal_var=False)[0]
    t[1] = ttest_ind(group1[group1_len:], group2[group2_len:], axis=0, equal_var=False)[0]
    return t

def leakage_func_bit(text, byte, bit, cipher, op_in, op_out):
    state = list(text)
    cipher._add_round_key(state, 0)
    if op_in == op_out:
        raise ValueError("Opin and opout can't be the same value!")

    states = []
    states.append([0]*16)
    for i in range(1, cipher._Nr):
        states.append(list(state))
        cipher._sub_bytes(state)

        states.append(list(state))
        cipher._shift_rows(state)

        states.append(list(state))
        cipher._mix_columns(state, False)

        states.append(list(state))
        cipher._add_round_key(state, i)

    states.append(list(state))
    cipher._sub_bytes(state)

    states.append(list(state))
    cipher._shift_rows(state)

    cipher._add_round_key(state, cipher._Nr)

    return (states[op_in][byte] ^ states[op_out][byte]) & (1 << bit)

def leakage_func_byte(text, byte, val, cipher, op_in, op_out):
    #bit unused
    state = list(text)
    cipher._add_round_key(state, 0)
    if op_in == op_out:
        raise ValueError("Opin and opout can't be the same value!")

    states = []
    states.append([0]*16)
    for i in range(1, cipher._Nr):
        states.append(list(state))
        cipher._sub_bytes(state)

        states.append(list(state))
        cipher._shift_rows(state)

        states.append(list(state))
        cipher._mix_columns(state, False)

        states.append(list(state))
        cipher._add_round_key(state, i)

    states.append(list(state))
    cipher._sub_bytes(state)

    states.append(list(state))
    cipher._shift_rows(state)

    cipher._add_round_key(state, cipher._Nr)

    return (states[op_in][byte] ^ states[op_out][byte]) == val

sbox_hw = lambda text, byte, bit, cipher, rnd: leakage_func_bit(text, byte, bit, cipher, 2+4*(rnd-1), 0)
roundout_hw = lambda text, byte, bit, cipher, rnd: leakage_func_bit(text, byte, bit, cipher, 2+4*(rnd-1)+3, 0)
roundinout_hd = lambda text, byte, bit, cipher, rnd: leakage_func_bit(text, byte, bit, cipher, 2+4*(rnd-1)-1, 2+4*(rnd-1)+3)
sboxinout_hd = lambda text, byte, bit, cipher, rnd: leakage_func_bit(text, byte, bit, cipher, 2+4*(rnd-1)-1, 2+4*(rnd-1))
generic_leakage_hw = lambda text, byte, bit, cipher, op_in: leakage_func_bit(text, byte, bit, cipher, op_in, 0)

def eval_rand_v_rand(waves, textins, func, key_len=16, round_range=None, byte_range=None, bit_range=None, plot=False):
    ktp = FixedVRandomText(key_len)
    cipher = ktp._dev_cipher
    if round_range is None:
        round_range = range(2, 9+(key_len//4 - 4) + 1)
    if byte_range is None:
        byte_range = range(0, 16)
    if bit_range is None:
        bit_range = range(0, 8)
    for rnd in round_range:
        for byte in byte_range:
            for bit in bit_range:
                truth_array = np.array([func(textins[i], byte, bit, cipher, rnd) for i in range(len(waves))])
                group1 = waves[truth_array != 0]
                group2 = waves[truth_array == 0]
                t_val = t_test(group1, group2)
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
                    plt.pause(0.0001)


def check_t_test(t):
    failed_points = []
    for i in range(len(t[0])):
        if ((t[0][i]) > 4.5) and ((t[1][i]) > 4.5):
            failed_points.append(i)
        elif ((t[0][i]) < -4.5) and ((t[1][i]) < -4.5):
            failed_points.append(i)

    return failed_points

def build_mean_corr(traces):
    mean = np.mean(traces, axis=0)
    print(len(mean))
    return traces-mean

def build_centered_product(mct):
    return np.multiply(mct, axis=1)