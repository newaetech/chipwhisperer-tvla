import logging
try:
    import chipwhisperer as cw
    import zarr
    from tqdm import trange
    from .ktp import FixedVRandomText, FixedVRandomKey, SemiFixedVRandomText, verify_AES
    from .analysis import t_test, check_t_test
    import numpy as np


    def setup_device(name):
        """Convience function for setting up and programing a CW/Target pair

        Args:
            name (str): String representing the target configuration. Currently
                        supports 'STM32F3', 'CW305', 'XMEGA', 'STM32F3-mbed',
                        'K82F', 'STM32F4'

        returns:
            Setup scope and target objects
        """
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

    def capture_non_specific(scope, target, ktp_class, N=10000, key_len=16, group1=None, group2=None):
        """ Capture data for a non-specific TVLA t-test

        Args:
            scope (CW scope object): Already setup scope object
            target (CW target object): Already setup target object
            ktp_class (ktp): Non specific KTP object (FixedVRandText, Key, etc)
            N (int): Number of traces to capture for each dataset (will end up with 2*N traces total)
            key_len (int): 16 for AES-128, 32 for AES-256
            group1 (np.array): Optional array object for storing traces in
            group2 (np.array): Optional array object for storing traces in

        Returns:
            group1, group2
        """
        ktp = ktp_class(key_len)
        if group1 is None:
            group1 = np.zeros((N, scope.adc.samples), dtype='float64')
        if group2 is None:
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

        return group1, group2

    def capture_rand(scope, target, N=10000, key_len=16, waves=None, textins=None):
        """ Capture traces for a rand_v_rand TVLA t-test

        Args:
            scope (CW scope object): Setup scope object
            target (CW target object): Setup target object
            N (int): Number of traces to capture
            key_len (int): 16 for AES-128, 32 for AES-256
            waves (np.array): Optional array object for storing traces in
            textins (np.array): Optional array object for storing plaintexts in

        Returns:
            waves, textins
        """
        ktp = FixedVRandomText(key_len)
        if waves is None:
            waves = np.zeros((N, scope.adc.samples), dtype='float64')
        if textins is None:
            textins = np.zeros((N, 16), dtype='uint8')
        for i in trange(N):
            key, text = ktp.next_group_B()
            trace = cw.capture_trace(scope, target, text, key)
            while trace is None:
                trace = cw.capture_trace(scope, target, text, key)
            if not verify_AES(text, key, trace.textout):
                raise ValueError("Encryption failed")

            waves[i,:] = trace.wave[:]
            textins[i,:] = np.array(text)[:]

        return waves, textins

    def capture_all(scope, target, platform, N=10000, key_len=16):
        """ Do all three non-specific captures and a Rand_V_Rand capture.

        Stores the results in a CWTVLA standard zarr array

        Args:
            scope (CW scope object): Setup scope object
            target (CW target object): Setup target object
            platform (str): What to call the set in the zarr array
            N (int): Number of traces to capture
            key_len (int): 16 for AES-128, 32 for AES-256
        """
        ktps = (FixedVRandomText, SemiFixedVRandomText, FixedVRandomKey)
        z = zarr.open_group("data/CWData.zarr", mode='a')
        z_plat = z.create_group("{}".format(platform), overwrite=True)
        for ktp in ktps:
            group1 = z_plat.zeros("{}-{}/traces/group1".format(ktp._name, key_len), shape=(N, scope.adc.samples), \
                chunks=(2500, None), dtype='float64')
            group2 = z_plat.zeros("{}-{}/traces/group2".format(ktp._name, key_len), shape=(N, scope.adc.samples), \
                chunks=(2500, None), dtype='float64')
            group1[:,:], group2[:,:] = capture_non_specific(scope, target, ktp, N, key_len)

        # do rand now
        waves = z_plat.zeros("RandVRand-{}/traces/waves".format(key_len), shape=(N, scope.adc.samples), \
            chunks=(2500, None), dtype='float64')
        textins = z_plat.zeros("RandVRand-{}/traces/textins".format(key_len), shape=(N, 16), \
            chunks=(2500, None), dtype='uint8')

        waves[:,:], textins[:,:] = capture_rand(scope, target, N, key_len) 

    def test_cw_non_specific(platform, key_len=16):
        """ Test a platform's non_specific traces

        Args:
            platform (str): The target object's name
            key_len (int): 16 for AES-128, 32 for AES-256
        """
        import matplotlib.pyplot as plt
        ktps = (FixedVRandomText, SemiFixedVRandomText, FixedVRandomKey)
        for ktp in ktps:
            group = zarr.open_group("data/CWData.zarr/{}/{}-{}".format(platform, ktp._name, key_len))
            group1 = group.traces.group1
            group2 = group.traces.group2
            t = group.zeros("results/tvla", shape=(2, len(group1[0])), dtype='float64', overwrite=True)
            t[0,:], t[1,:] = t_test(group1[:,:], group2[:,:])
            fail_points = check_t_test(t)
            if len(fail_points) > 0:
                print("Failed at {}".format(fail_points))
            else:
                print("passed test")
            plt.figure()
            plt.plot(t[0])
            plt.plot(t[1])
            plt.show()

except Exception as e:
    logging.error("Unable to import chipwhisperer, convenience functions unavailable")
    logging.error("Got error {}".format(str(e)))
