# do capture for TVLA

#... setup, get scope, target
import chipwhisperer as cw
scope = cw.scope()
target = cw.target(scope)
scope.default_setup()

# capture traces...
N = 50000 #total traces = 2*n

from cwtvla.ktp import FixedVRandomText, verify_AES
key_len = 16
ktp = FixedVRandomText(key_len)

group1 = np.zeros((N, scope.adc.samples), dtype='float64')
group2 = np.zeros((N, scope.adc.samples), dtype='float64')
for i in trange(N):
    key, text = ktp.next_group_A()

    trace = cw.capture_trace(scope, target, text, key)
    while trace is None:
        trace = cw.capture_trace(scope, target, text, key)

    if not verify_AES(text, key, trace.textout):
        raise ValueError("Encryption failed")
    group1[i,:] = trace.wave[:]

    key, text = ktp.next_group_B() 
    trace = cw.capture_trace(scope, target, text, key)
    while trace is None:
        trace = cw.capture_trace(scope, target, text, key)

    group2[i,:] = trace.wave[:]
    if not verify_AES(text, key, trace.textout):
        raise ValueError("Encryption failed")

# do analysis
from cwtvla.analysis import t_test, check_t_test
t_val = t_test(group1, group2)
fp = check_t_test(t_val)

if len(fp) > 0:
    print("Failed T Test @ {}".format(fp))
else:
    print("Passed T Test")

import matplotlib.pyplot as plt 
plt.figure()
plt.plot(t_val[0])
plt.plot(t_val[1])
plt.show()