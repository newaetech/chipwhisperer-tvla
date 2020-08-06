import numpy as np
from scipy.stats import ttest_ind
import chipwhisperer as cw
from aes_cipher import AESCipher
from ktp import verify_AES

def create_projects(name):
    group_1 = cw.create_project("TVLA_{}_group_1".format(name), overwrite=True)
    group_2 = cw.create_project("TVLA_{}_group_2".format(name), overwrite=True)
    return group_1, group_2


def do_tvla(scope, target, tvla_obj, N, key_len=16, save=False):
    import chipwhisperer as cw
    ktp = tvla_obj(key_len)
    projects = create_projects(ktp._name)

    for i in range(N):
        key, text = ktp.next_group_A() 
        trace = cw.capture_trace(scope, target, text, key)
        while trace is None:
            trace = cw.capture_trace(scope, target, text, key)

        if not verify_AES(text, key, trace.textout):
            raise ValueError("Encryption failed")
        projects[0].traces.append(trace)

        key, text = ktp.next_group_B() 
        trace = cw.capture_trace(scope, target, text, key)
        while trace is None:
            trace = cw.capture_trace(scope, target, text, key)
        projects[1].traces.append(trace)
        if not verify_AES(text, key, trace.textout):
            raise ValueError("Encryption failed")

    t = t_test(projects)
    projects[0].close(save=save)
    projects[1].close(save=save)
    return t


def t_test(projects):
    group_len = len(projects[0].traces) // 2
    trace_len = len(projects[0].waves[0])
    project_1_np = [np.zeros([trace_len, group_len]), np.zeros([trace_len, group_len])]
    project_2_np = [np.zeros([trace_len, group_len]), np.zeros([trace_len, group_len])]
    t = np.zeros([trace_len, 2])

    for i in range(group_len):
        project_1_np[0][:,i] = projects[0].waves[i]
        project_1_np[1][:,i] = projects[0].waves[i + group_len]
        project_2_np[0][:,i] = projects[1].waves[i]
        project_2_np[1][:,i] = projects[1].waves[i + group_len]

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
