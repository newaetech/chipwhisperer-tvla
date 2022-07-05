import warnings
from .aes_cipher import AESCipher
from .key_schedule import key_schedule_rounds
import numpy as np
import random

def hexstr2list(data):
    """Convert a string with hex numbers into a list of numbers"""

    data = str(data)

    newdata = data.lower()
    newdata = newdata.replace("0x", "")
    newdata = newdata.replace(",", "")
    newdata = newdata.replace(" ", "")
    newdata = newdata.replace("[", "")
    newdata = newdata.replace("]", "")
    newdata = newdata.replace("(", "")
    newdata = newdata.replace(")", "")
    newdata = newdata.replace("{", "")
    newdata = newdata.replace("}", "")
    newdata = newdata.replace(":", "")
    newdata = newdata.replace("-", "")

    datalist = [int(newdata[i:(i + 2)], 16) for i in range(0, len(newdata), 2)]

    return datalist

def hexStrToByteArray(hexStr):
    ba = bytearray(hexstr2list(hexStr))
    return ba

def _expand_aes_key(key):
    rounds = 0
    start = 1
    if len(key) == 16:
        rounds = 10
    elif len(key) == 24:
        rounds = 12
    elif len(key) == 32:
        rounds = 14
        start = 2
    else:
        raise ValueError("Invalid AES key length: {}".format(len(key)))

    exp_key = list(key)
    for i in range(start, rounds+1):
        exp_key.extend(key_schedule_rounds(list(key), 0, i))

    return exp_key

def verify_AES(plaintext, key, ciphertext):
    """ Verifies that AES(plaintext, key) == ciphertext
    """
    key_exp = _expand_aes_key(key)
    cipher = AESCipher(key_exp)
    calc_ciphertext = bytearray(cipher.cipher_block(list(plaintext)))
    return (ciphertext == calc_ciphertext)


class FixedVRandomText:
    """ Key text pairs for FixedVRandomText TVLA

    Useful for evaluating the general leakage of a device, but
    may pick up false positives from loading/unloading of key/plaintext.

    Usage::

        import cwtvla
        ktp = cwtvla.tkp.FixedVRandomText(key_len=16) #16 byte key - AES128
        key, text ktp.next_group_A() # Fixed text, fixed key
        key, text ktp.next_group_B() # Random text, fixed key

    :code:`next_group_B()` can also be used for Random V Random captures
    """
    _name = "FixedVRandomText"
    def __init__(self, key_len=16):
        self._key_len = key_len
        self._I_0 = bytearray([0x00] * 16)
        self.rounds = 10
        if key_len == 16:
            self._I_fixed = hexStrToByteArray("da 39 a3 ee 5e 6b 4b 0d 32 55 bf ef 95 60 18 90")
            self._K_dev = hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0")
            self._K_gen = hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd e0 f0")
        elif key_len == 24:
            self.rounds = 12
            self._I_fixed = hexStrToByteArray("da 39 a3 ee 5e 6b 4b 0d 32 55 bf ef 95 60 18 88")
            self._K_dev = hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0 23 45 67 89 ab cd ef 01")
            self._K_gen = hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de 0f 01") 
        elif key_len == 32:
            self.rounds = 14
            self._I_fixed = hexStrToByteArray("da 39 a3 ee 5e 6b 4b 0d 32 55 bf ef 95 60 18 95")
            self._K_dev = hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0 23 45 67 89 ab cd ef 01 34 56 78 9a bc de f0 12")
            self._K_gen = hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de f0 13 45 67 89 ab cd e0 f0 12")
        else:
            raise ValueError("Invalid key length {}, must be 16, 24, or 32".format(key_len))

        self._K_gen_exp = _expand_aes_key(self._K_gen)
        self._K_dev_exp = _expand_aes_key(self._K_dev)
        self._cipher = AESCipher(self._K_gen_exp)
        self._dev_cipher = AESCipher(self._K_dev_exp)

    def next_group_A(self):
        """Return key, text, ciphertext for fixed text group"""
        return self._K_dev, self._I_fixed

    def next_group_B(self):
        """Return key, text for random group. Updates random group afterwards

        1st Call: I0

        2nd Call: I1

        3rd Call: I2..."""
        pt = self._I_0
        self._I_0 = bytearray(self._cipher.cipher_block(list(self._I_0)))
        return self._K_dev, pt


class FixedVRandomKey:
    """ Key text pairs for FixedVRandomKey TVLA

    Usage::

        import cwtvla
        ktp = cwtvla.tkp.FixedVRandomKey(key_len=16) #16 byte key - AES128
        key, text ktp.next_group_A() # Random text, fixed key
        key, text ktp.next_group_B() # Random text, Random key

    """
    _name = "FixedVRandomKey"
    def __init__(self, key_len=16):
        self._key_len = key_len
        self._I_0_fixed = bytearray([0xAA] * 16)
        self._I_0_rand = bytearray([0xCC] * 16)
        self._K_0 = hexStrToByteArray("53 53 53 53 53 53 53 53 53 53 53 53 53 53 53 53")
        rounds = 10
        if key_len == 16:
            self._K_fixed = hexStrToByteArray("81 1E 37 31 B0 12 0A 78 42 78 1E 22 B2 5C DD F9")
            self._K_gen = hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd e0 f0")
        elif key_len == 24:
            rounds = 12
            self._K_fixed = hexStrToByteArray("81 1E 37 31 B0 12 0A 78 42 78 1E 22 B2 5C DD F9 94 F4 D9 2C D2 FA E6 45")
            self._K_gen =hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de 0f 01") 
        elif key_len == 32:
            rounds = 14
            self._K_fixed = hexStrToByteArray("81 1E 37 31 B0 12 0A 78 42 78 1E 22 B2 5C DD F9 94 F4 D9 2C D2 FA E6 45 37 B9 40 EA 5E 1A F1 12")
            self._K_gen = hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de f0 13 45 67 89 ab cd e0 f0 12")
        else:
            raise ValueError("Invalid key length {}, must be 16, 24, or 32".format(key_len))

        self._K_gen_exp = _expand_aes_key(self._K_gen)
        self._cipher = AESCipher(self._K_gen_exp)

    def next_group_A(self):
        key = self._K_fixed
        text = self._I_0_fixed
        self._I_0_fixed = bytearray(self._cipher.cipher_block(list(self._I_0_fixed)))
        return key, text

    def next_group_B(self):
        key = self._K_0
        self._K_0 = bytearray(self._cipher.cipher_block(list(self._K_0)))
        if self._key_len == 24:
            key.extend(self._K_0[:8])
            self._K_0 = bytearray(self._cipher.cipher_block(list(self._K_0)))
        elif self._key_len == 32:
            key.extend(self._K_0)
            self._K_0 = bytearray(self._cipher.cipher_block(list(self._K_0)))

        text = self._I_0_rand
        self._I_0_rand = bytearray(self._cipher.cipher_block(list(text)))

        return key, text

class SemiFixedVRandomText:
    """ Key text pairs for SemiFixedVRandomText.

    Sets state in selected round to 0x8B8A490BDF7C00BDD7E6066Cxxxxxxxx. Varies the last bits
    and reverses to get input plaintext.

    Useful since it is both non-specific and restricts TVLA results to a middle round.

    Usage::

        import cwtvla
        ktp = cwtvla.tkp.SemiFixedVRandomText(key_len=16, round=5) #16 byte key - AES128, reverse from round 5
        key, text ktp.next_group_A() # Semi fixed text, Fixed key
        key, text ktp.next_group_B() # Random text, Fixed key 

    """
    _name = "SemiFixedVRandomText"
    def __init__(self, key_len=16, round=None):
        self._key_len = key_len
        self._I_0 = bytearray([0x00] * 16)
        rounds = 10
        random.seed()
        self._round = round
        self._I_semi_fixed = hexStrToByteArray("8B 8A 49 0B DF 7C 00 BD D7 E6 06 6C 61 00 24 12")
        if key_len == 16:
            if not round:
                self._round = 5
            self._K_dev = hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0")
            self._K_gen = hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd e0 f0")
        elif key_len == 24:
            rounds = 12
            if not round:
                self._round = 6
            self._K_dev = hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0 23 45 67 89 ab cd ef 01")
            self._K_gen = hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de 0f 01") 
        elif key_len == 32:
            if not round:
                self._round = 7
            rounds = 14
            self._K_dev = hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0 23 45 67 89 ab cd ef 01 34 56 78 9a bc de f0 12")
            self._K_gen = hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de f0 13 45 67 89 ab cd e0 f0 12")
        else:
            raise ValueError("Invalid key length {}, must be 16, 24, or 32".format(key_len))

        self._K_dev_exp = _expand_aes_key(self._K_dev)
        self._K_gen_exp = _expand_aes_key(self._K_gen)

        self._dev_cipher = AESCipher(self._K_dev_exp)
        self._cipher = AESCipher(self._K_gen_exp)
        self._state_start = np.uint32(int.from_bytes(self._I_semi_fixed[:4], "big"))

    def _invert_from_round(self, plaintext):
        # todo: maybe make round an argument?
        text = list(plaintext)
        text = text + [0]*(16 - len(text))

        # assuming each round is finished at the end of add round key, starting with round 0
        # i.e. round 1 is after the second add round key
        for round in range(self._round, 0, -1):
            self._dev_cipher._add_round_key(text, round) #invert add round key
            self._dev_cipher._mix_columns(text, True) #
            self._dev_cipher._i_shift_rows(text)
            self._dev_cipher._i_sub_bytes(text)

        self._dev_cipher._add_round_key(text, 0)
        return bytearray(text)

    def next_group_A(self):
        #update round x state
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            self._state_start += 1

        x = int(self._state_start).to_bytes(4, "big")
        #x = random.getrandbits(32)
        for i in range(4):
            self._I_semi_fixed[-i-1] = x[i]
            #self._I_semi_fixed[-i-1] = (x >> 8*i) & 0xFF


        #invert to start of AES
        text = self._invert_from_round(self._I_semi_fixed)
        return self._K_dev, text

    def next_group_B(self):
        """Return key, text for random group. Updates random group afterwards

        1st Call: I0
        2nd Call: I1
        3rd Call: I2..."""
        pt = self._I_0
        self._I_0 = bytearray(self._cipher.cipher_block(list(self._I_0)))
        return self._K_dev, pt


if __name__ == "__main__":
    ktp = SemiFixedVRandomText()
    ktp._dev_cipher.cipher_block([0]*16)
    b = bytearray([19, 50, 96, 23, 9, 13, 146, 189, 174, 31, 10, 50, 36, 174, 191, 16])
    a = ktp._invert_from_round(b)
    print(a)
    print(b)