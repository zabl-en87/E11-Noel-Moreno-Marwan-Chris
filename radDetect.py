import sys
sys.path.append('/home/pi/cape_mca') #capemca.py directory
from capemca import *
import csv
import time
import numpy as np
import matplotlib.pyplot as plt

dataName = sys.argv[4]

file = open(dataName, 'w', newline = '')
spamwriter = csv.writer(file, delimiter=',')

devices = find_all_mcas()
print(f"Found {len(devices)} MCA device(s)")
        
if not devices:
        sys.exit(1)

duration = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
window = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
name = sys.argv[3]
    

spectra = [] #originally called spectra
read_times = []

with CapeMCA() as mca:
        try:
                start = time.time()
                reads = 0
                next_read = start
        
                while time.time() - start < duration:
                        # Wait until the next window boundary
                        now = time.time()
                        if now < next_read:
                                time.sleep(next_read - now)

                        read_start = time.time()
                        status = mca.read_status()
                        spectrum = mca.read_spectrum()
                        read_end = time.time()
        
                        # Schedule next read from when this one started
                        next_read = read_start + window

                        spec_data = spectrum[1:]
                        spec_total = sum(spec_data)
                        nonzero = sum(1 for ch in spec_data if ch > 0)
                        elapsed = read_start - start

                        print(f"[{elapsed:6.1f}s] read {reads+1} "
                              f"(took {read_end - read_start:.2f}s): "
                              f"{status.cps} cps, "
                              f"totalCount={status.total_count:g}, "
                              f"intervals={status.total_intervals}")
                        print(f"         spectrum: ch0={spectrum[0]}, specSum={spec_total}, "
                              f"nonzeroCh={nonzero}")

                        active = [(ch, spectrum[ch]) for ch in range(1, SPECTRUM_CHANNELS)
                                  if spectrum[ch] > 0]
                        print(f"         channels: {active}")

                
                        spectra.append(spec_data)
                        spamwriter.writerow([read_end - read_start, spec_total])
                        read_times.append(elapsed)
                        reads += 1

                    print(f"\nCompleted {reads} reads in {time.time() - start:.2f}s "
                          f"(window={window}s)")

                except Exception as e:
                    print(f"\nError after {reads} reads: {e}")

            print("Device closed, exiting.")


file.close()


