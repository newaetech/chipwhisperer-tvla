import zarr
import numpy as np
from scipy.stats import ttest_ind 
from tqdm import trange
from .ktp import FixedVRandomText
import matplotlib.pyplot as plt
import tqdm


def leakage_lookup(operation, round):
    """ Get the number representation for operation happening in round

    Args:
        operation (str, None): One of 'subbytes', 'shiftrows', 'mixcolumns', or 'addroundkey'.
                                If None, 0 is returned
        round (int): Which round the operation is occuring in

    Returns:
        A number corresponding to the desired operation

    """
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
    """ Perform a t_test between two numpy arrays.

    Splits the data between the first and second half of each group

    Args:
        group1 (numpy.array): Group 1
        group2 (numpy.array): Group 2

    Returns:
        A numpy with two elements spanning the length of the traces. The
        first is between the first half of groups 1 and 2. The second
        is between the second half of the groups.
    """
    trace_len = len(group1[0])
    group1_len = len(group1) // 2
    group2_len = len(group2) // 2
    t = np.zeros([2, trace_len], dtype='float64')
    t[0] = ttest_ind(group1[:group1_len], group2[:group2_len], axis=0, equal_var=False)[0]
    t[1] = ttest_ind(group1[group1_len:], group2[group2_len:], axis=0, equal_var=False)[0]
    return t

def leakage_func_bit(text, byte, bit, cipher, op_in, op_out):
    """ A generic leakage function for testing a bit in the AES state

    Tests between operations op_in and op_out. Assuming st0 is the state
    after operation op_in and st1 is the state after operation op_out,
    returns (st0[byte] ^ st1[byte]) & (1 << bit)

    Args:
        text (list): The input plaintext
        byte (int): Which byte to get the leakage for
        bit (int): Which bit to get the leakage for
        cipher (AESCipher): The cipher used for encryption
        op_in (int): Use the state after operation op_in. If 0, an array of 0 is used (useful for HW)
        op_out (int): Use the state after operation op_out. If 0, an array of 0 is used (useful for HW)

    Returns:
        1 if the bit under test is 1, 0 if it is 0
    """
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

    return (((states[op_in][byte] ^ states[op_out][byte]) >> bit) & 1) == 1

def leakage_func_byte(text, byte, val, cipher, op_in, op_out):
    """ A generic leakage function for testing the value AES state

    Tests between operations op_in and op_out. Assuming st0 is the state
    after operation op_in and st1 is the state after operation op_out,
    returns (st0[byte] ^ st1[byte]) == val

    Args:
        text (list): The input plaintext
        byte (int): Which byte to get the leakage for
        val (int): The val to separate based on
        cipher (AESCipher): The cipher used for encryption
        op_in (int): Use the state after operation op_in. If 0, an array of 0 is used (useful for HW)
        op_out (int): Use the state after operation op_out. If 0, an array of 0 is used (useful for HW)

    Returns:
        1 if the bit under test is 1, 0 if it is 0
    """
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

def construct_leakage(func, operation_in, operation_out):
    return lambda text, byte, bit, cipher, rnd: func(text, byte, bit, cipher, leakage_lookup(operation_in, rnd), leakage_lookup(operation_out, rnd))

def eval_rand_v_rand(waves, textins, func, key_len=16, round_range=None, byte_range=None, bit_range=None, plot=False):
    """ Evaluate rand_v_rand traces using a leakage function.

    Separates waves using textins and the leakage func, then does a t_test between them.

    Done for rounds in round_range, for bytes in byte_range, and bits (or vals) in bit range. Can
    also plot for each test.

    Args:
        waves (np.array): Rand V Rand Trace waves
        textins (np.array): Rand V Rand plaintexts
        func (function(textin, byte, bit, cipher, round)): Leakage to function used to separate traces
        key_len (int): length of key used in bytes
        round_range (iterable): Rounds to test
        byte_range (iterable): Bytes to test
        bit_range (iterable): Bits to test (or vals if using a byte leakage func)
        plot (bool): Plot t_test results?

    """
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
    """Check the results of the t_test and return points where it failed.
    """
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