from chipwhisperer.common.utils import util
import warnings
from chipwhisperer.common.utils.aes_cipher import AESCipher
from chipwhisperer.analyzer.utils.aes_funcs import key_schedule_rounds
import numpy as np

class FixedVRandomText:
    _name = "FixedVRandomText"
    def __init__(self, key_len=16):
        self._key_len = key_len
        self._I_0 = bytearray([0x00] * 16)
        rounds = 10
        if key_len == 16:
            self._I_fixed = util.hexStrToByteArray("da 39 a3 ee 5e 6b 4b 0d 32 55 bf ef 95 60 18 90")
            self._K_dev = util.hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0")
            self._K_gen = util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd e0 f0")
        elif key_len == 24:
            rounds = 12
            self._I_fixed = util.hexStrToByteArray("da 39 a3 ee 5e 6b 4b 0d 32 55 bf ef 95 60 18 88")
            self._K_dev = util.hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0 23 45 67 89 ab cd ef 01")
            self._K_gen = util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de 0f 01") 
        elif key_len == 32:
            rounds = 14
            self._I_fixed = util.hexStrToByteArray("da 39 a3 ee 5e 6b 4b 0d 32 55 bf ef 95 60 18 95")
            self._K_dev = util.hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0 23 45 67 89 ab cd ef 01 34 56 78 9a bc de f0 12")
            self._K_gen = util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de f0 13 45 67 89 ab cd e0 f0 12")
        else:
            raise ValueError("Invalid key length {}, must be 16, 24, or 32".format(key_len))

        self._K_gen_exp = list(self._K_gen)
        for i in range(rounds):
            self._K_gen_exp.extend(key_schedule_rounds(list(self._K_gen), 0, i))
        self._cipher = AESCipher(self._K_gen_exp)

    def next_group_A(self):
        """Return key, text for fixed text group"""
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
    _name = "FixedVRandomKey"
    def __init__(self, key_len=16):
        self._key_len = key_len
        self._I_0_fixed = bytearray([0xAA] * 16)
        self._I_0_rand = bytearray([0xCC] * 16)
        self._K_0 = util.hexStrToByteArray("53 53 53 53 53 53 53 53 53 53 53 53 53 53 53 53")
        rounds = 10
        if key_len == 16:
            self._K_fixed = util.hexStrToByteArray("81 1E 37 31 B0 12 0A 78 42 78 1E 22 B2 5C DD F9")
            self._K_gen = util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd e0 f0")
        elif key_len == 24:
            rounds = 12
            self._K_fixed = util.hexStrToByteArray("81 1E 37 31 B0 12 0A 78 42 78 1E 22 B2 5C DD F9 94 F4 D9 2C D2 FA E6 45")
            self._K_gen =util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de 0f 01") 
        elif key_len == 32:
            rounds = 14
            self._K_fixed = util.hexStrToByteArray("81 1E 37 31 B0 12 0A 78 42 78 1E 22 B2 5C DD F9 94 F4 D9 2C D2 FA E6 45 37 B9 40 EA 5E 1A F1 12")
            self._K_gen = util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de f0 13 45 67 89 ab cd e0 f0 12")
        else:
            raise ValueError("Invalid key length {}, must be 16, 24, or 32".format(key_len))

        self._K_gen_exp = list(self._K_gen)
        for i in range(rounds):
            self._K_gen_exp.extend(key_schedule_rounds(list(self._K_gen), 0, i))

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
    _name = "SemiFixedVRandomText"
    def __init__(self, key_len=16, round=None):
        self._key_len = key_len
        self._I_0 = bytearray([0x00] * 16)
        rounds = 10
        self._I_semi_fixed = util.hexStrToByteArray("8B 8A 49 0B DF 7C 00 BD D7 E6 06 6C 61 00 24 12")
        if key_len == 16:
            if not round:
                self._round = 5
            self._K_dev = util.hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0")
            self._K_gen = util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd e0 f0")
        elif key_len == 24:
            rounds = 12
            if not round:
                self._round = 6
            self._K_dev = util.hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0 23 45 67 89 ab cd ef 01")
            self._K_gen = util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de 0f 01") 
        elif key_len == 32:
            if not round:
                self._round = 7
            rounds = 14
            self._K_dev = util.hexStrToByteArray("01 23 45 67 89 ab cd ef 12 34 56 78 9a bc de f0 23 45 67 89 ab cd ef 01 34 56 78 9a bc de f0 12")
            self._K_gen = util.hexStrToByteArray("12 34 56 78 9a bc de f1 23 45 67 89 ab cd ef 02 34 56 78 9a bc de f0 13 45 67 89 ab cd e0 f0 12")
        else:
            raise ValueError("Invalid key length {}, must be 16, 24, or 32".format(key_len))

        self._K_dev_exp = list(self._K_dev)
        self._K_gen_exp = list(self._K_gen)

        for i in range(rounds):
            self._K_dev_exp.extend(key_schedule_rounds(list(self._K_dev), 0, i))
            self._K_gen_exp.extend(key_schedule_rounds(list(self._K_gen), 0, i))

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

        self._dev_cipher._add_round_key(text, round)
        return bytearray(text)

    def next_group_A(self):
        #update round x state
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            self._state_start += 1

        self._I_semi_fixed[:4] = int(self._state_start).to_bytes(4, "big")

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




