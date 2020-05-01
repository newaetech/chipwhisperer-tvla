import chipwhisperer as cw
import sys
from tqdm import trange
from Crypto.Cipher import AES
from chipwhisperer.common.utils import util
from scipy.stats import ttest_ind
import numpy as np
import time
from ktp import FixedVRandomText, FixedVRandomKey, SemiFixedVRandomText

import matplotlib.pyplot as plt

N = 100

def setup_cw(programmer, path):
    scope = cw.scope()
    target = cw.target(scope)
    scope.default_setup()
    scope.adc.samples = 24400
    scope.adc.offset = 10000 
    time.sleep(0.05)
    cw.program_target(scope, programmer, path)
    return scope, target

def create_projects(name):
    group_1 = cw.create_project("TVLA_{}_group_1".format(name), overwrite=True)
    group_2 = cw.create_project("TVLA_{}_group_2".format(name), overwrite=True)
    return group_1, group_2

def perform_test(platform, tvla_obj, plot=False):
    if platform == "xmega":
        scope, target = setup_cw(cw.programmers.XMEGAProgrammer, "AES-xmega.hex")
        N = 100
    elif platform == "stm":
        scope, target = setup_cw(cw.programmers.STM32FProgrammer, "AES-mbed.hex")
        N = 100
    elif platform == "CW305":
        scope = cw.scope()

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
        N = 2500

    ktp = tvla_obj(16)
    fixed_project, random_project = create_projects(ktp._name)

    #collect group1 data
    for i in trange(N):
        key, text = ktp.next_group_A() 
        trace = cw.capture_trace(scope, target, text, key)
        while trace is None:
            trace = cw.capture_trace(scope, target, text, key)

        fixed_project.traces.append(trace)

        key, text = ktp.next_group_B() 
        trace = cw.capture_trace(scope, target, text, key)
        while trace is None:
            trace = cw.capture_trace(scope, target, text, key)
        random_project.traces.append(trace)



    print(scope.adc.trig_count)
    fixed_project.save()
    random_project.save()
    t = t_test(fixed_project, random_project)

    fail_points = check_t_test(t)
    if len(fail_points) > 0:
        print("Test failed at points {}".format(fail_points))
    else:
        print("Passed test")

    if plot:
        plt.plot(t[0])
        plt.plot(t[1])
        plt.show()

    scope.dis()
    target.dis()

def t_test(project_1, project_2):
    group_len = len(project_1.traces) // 2
    trace_len = len(project_1.waves[0])
    project_1_np = [np.zeros([trace_len, group_len]), np.zeros([trace_len, group_len])]
    project_2_np = [np.zeros([trace_len, group_len]), np.zeros([trace_len, group_len])]
    t = np.zeros([trace_len, 2])

    for i in range(group_len):
        project_1_np[0][:,i] = project_1.waves[i]
        project_1_np[1][:,i] = project_1.waves[i + group_len]
        project_2_np[0][:,i] = project_2.waves[i]
        project_2_np[1][:,i] = project_2.waves[i + group_len]

    t = np.zeros([2, trace_len])
    for i in range(trace_len):
        t[0][i] = ttest_ind(project_1_np[0][i], project_2_np[0][i], equal_var=False)[0]
        t[1][i] = ttest_ind(project_1_np[1][i], project_2_np[1][i], equal_var=False)[0]

    return t

def check_t_test(t):
    failed_points = []
    for i in range(len(t[0])):
        if ((t[0][i]) > 4.5) and ((t[1][i]) > 4.5):
            failed_points.append(i)
        elif ((t[0][i]) < -4.5) and ((t[1][i]) < -4.5):
            failed_points.append(i)

    return failed_points


#perform_test("xmega", SemiFixedVRandomText, True)
#perform_test("xmega", FixedVRandomKey, True)
#perform_test("xmega", FixedVRandomText, True)

#perform_test("stm", SemiFixedVRandomText, True)
perform_test("stm", FixedVRandomKey, True)
perform_test("stm", FixedVRandomText, True)

#perform_test("CW305", SemiFixedVRandomText, True)
#perform_test("CW305", FixedVRandomKey, True)
#perform_test("CW305", FixedVRandomText, True)