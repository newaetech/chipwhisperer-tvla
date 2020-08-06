import chipwhisperer as cw
import time
from .ktp import FixedVRandomText, FixedVRandomKey, SemiFixedVRandomText
from .tvla_cw import do_tvla, check_t_test
import matplotlib.pyplot as plt

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

perform_test("STM32F4", SemiFixedVRandomText, plot=True)
#perform_test("STM32F4", FixedVRandomKey, plot=True)
#perform_test("STM32F4", FixedVRandomText, plot=True)

#perform_test("CW305", SemiFixedVRandomText, plot=True)
#perform_test("CW305", FixedVRandomKey, plot=True)
#perform_test("CW305", FixedVRandomText, True)

#perform_test("K82F", SemiFixedVRandomText, 32, True)
#perform_test("K82F", FixedVRandomKey, 32, True)
#perform_test("K82F", FixedVRandomText, 32, True)