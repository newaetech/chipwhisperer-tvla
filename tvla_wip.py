import chipwhisperer as cw
import sys
from Crypto.Cipher import AES
from chipwhisperer.common.utils import util
from scipy.stats import ttest_ind
import numpy as np
import time
from fixed_v_random_text import FixedVRandomText, FixedVRandomKey, SemiFixedVRandomText

import matplotlib.pyplot as plt

N = 500


def perform_test(tvla_obj, plot=False):
    scope = cw.scope()
    target = cw.target(scope)
    scope.default_setup()
    scope.adc.samples = 24400
    time.sleep(0.05)
    ktp = tvla_obj(16)
    fixed_project = cw.create_project("TVLA_{}_group_1".format(ktp._name), overwrite=True)
    random_project = cw.create_project("TVLA_{}_group_2".format(ktp._name), overwrite=True)

    cw.program_target(scope, cw.programmers.STM32FProgrammer, "F:/chipwhisperer-tvla/AES.hex")

    #do fixed test
    for i in range(N):
        key, text = ktp.next_group_A() 
        trace = cw.capture_trace(scope, target, text, key)
        while trace is None:
            trace = cw.capture_trace(scope, target, text, key)

        fixed_project.traces.append(trace)


    #do random test
    for i in range(N):
        key, text = ktp.next_group_B() 
        trace = cw.capture_trace(scope, target, text, key)
        while trace is None:
            trace = cw.capture_trace(scope, target, text, key)

        random_project.traces.append(trace)


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
        if (abs(t[0][i]) > 4.5) and (abs(t[1][i]) > 4.5):
            failed_points.append(i)
    return failed_points


perform_test(SemiFixedVRandomText, True)
perform_test(FixedVRandomKey, True)
perform_test(FixedVRandomText, True)
