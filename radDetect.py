import sys
sys.path.append('/home/pi/cape_mca') #capemca.py directory
from capemca import *
import csv

dataName = sys.argv[4]

with open(dataName, 'w', newline = '') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',')
        




        if __name__ == '__main__':
            import sys
            import time
            import numpy as np
            import matplotlib.pyplot as plt

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
                        spamwriter.writerow({read_end - read_start:.2f}s, {status.total_count:g})
                        read_times.append(elapsed)
                        reads += 1

                    print(f"\nCompleted {reads} reads in {time.time() - start:.2f}s "
                          f"(window={window}s)")

                except Exception as e:
                    print(f"\nError after {reads} reads: {e}")

            print("Device closed, exiting.")

    

    if spectra:
        waterfall = np.array(spectra)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # Top: waterfall heatmap — channels vs read number
        im = ax1.imshow(waterfall, aspect='auto', origin='lower',
                        extent=[1, SPECTRUM_CHANNELS - 1, 0.5, len(spectra) + 0.5],
                        interpolation='nearest', cmap='hot')
        ax1.set_xlabel("Channel")
        ax1.set_ylabel("Read #")
        ax1.set_title(f"Spectrum waterfall ({window}s window)")
        # Label y-axis ticks with timestamps
        yticks = list(range(1, len(spectra) + 1))
        ylabels = [f"{reads} ({t:.0f}s)" for reads, t in zip(yticks, read_times)]
        ax1.set_yticks(yticks)
        ax1.set_yticklabels(ylabels, fontsize=7)
        fig.colorbar(im, ax=ax1, label="Counts")

        # Bottom: summed spectrum (log scale)
        summed = waterfall.sum(axis=0)
        ax2.plot(range(1, SPECTRUM_CHANNELS), summed, 'k-', linewidth=0.8)
        ax2.set_yscale('log')
        ax2.set_xlabel("Channel")
        ax2.set_ylabel("Counts (summed)")
        ax2.set_title(f"Summed spectrum ({len(spectra)} reads, {window}s windows)")

        plt.tight_layout()
        plt.savefig(name, dpi=150)
        print("Plot saved to spectra.png")
        plt.show()
