"""
Communication module for the CapeSym MCA radiation sensor.

Requires:
    sudo apt install libusb-1.0-0-dev
    pip install pyusb

For non-root USB access on Raspberry Pi, create /etc/udev/rules.d/50-capemca.rules:
    SUBSYSTEMS=="usb",ATTRS{idVendor}=="4701",ATTRS{idProduct}=="0290",GROUP="users",MODE="0666"
Then reboot or run: sudo udevadm control --reload-rules && sudo udevadm trigger
"""

import struct
import usb.core
import usb.util

VENDOR_ID = 0x4701
PRODUCT_ID = 0x0290
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81
TIMEOUT_MS = 10000

SPECTRUM_CHANNELS = 4096

# Run mode commands: [byte1, byte2]
CMD_PACKET0 = bytes([0, 0])       # Request 64-byte status packet (undocumented legacy)
CMD_SPECTRUM_1K = bytes([0, 4])   # Request 1024-channel spectrum (4096 bytes)
CMD_SPECTRUM_2K = bytes([0, 8])   # Request 2048-channel spectrum (8192 bytes)
CMD_SPECTRUM = bytes([0, 16])     # Request 4096-channel spectrum (16384 bytes)
CMD_ZERO_SPECTRUM = bytes([1, 1]) # Zero out all spectrum channels
CMD_STOP = bytes([2, 2])          # Stop MCA, enter Stop mode
CMD_READ_PARAMS = bytes([3, 3])   # Return 128 x int32 parameters (512 bytes)

NUM_PARAMS = 128

# struct format for PACKET0_TYPE (64 bytes, little-endian)
#   3 floats:  cps, totalCount, totalPulseTime
#   6 uint32s: usPerInterval, totalIntervals, capemcaId, detectors, cpiArray, countInRangeArray
#   3 floats:  xDirection, yDirection, zDirection
#   4 uint32s: reserved
PACKET0_FORMAT = '<3f6I3f4I'
PACKET0_SIZE = struct.calcsize(PACKET0_FORMAT)  # 64


class Packet0:
    """Status/metadata packet from the MCA."""

    __slots__ = (
        'cps', 'total_count', 'total_pulse_time',
        'us_per_interval', 'total_intervals', 'capemca_id',
        'detectors', 'cpi_array', 'count_in_range_array',
        'x_direction', 'y_direction', 'z_direction',
    )

    def __init__(self, data: bytes):
        fields = struct.unpack(PACKET0_FORMAT, data)
        self.cps = fields[0]
        self.total_count = fields[1]
        self.total_pulse_time = fields[2]
        self.us_per_interval = fields[3]
        self.total_intervals = fields[4]
        self.capemca_id = fields[5]
        self.detectors = fields[6]
        self.cpi_array = fields[7]
        self.count_in_range_array = fields[8]
        self.x_direction = fields[9]
        self.y_direction = fields[10]
        self.z_direction = fields[11]
        # fields[12:16] are reserved

    def __repr__(self):
        lines = [
            f"  cps:                {self.cps:g}",
            f"  totalCount:         {self.total_count:g}",
            f"  totalPulseTime:     {self.total_pulse_time:g} s",
            f"  usPerInterval:      {self.us_per_interval}",
            f"  totalIntervals:     {self.total_intervals}",
            f"  capemcaId:          {self.capemca_id}",
        ]
        if self.detectors > 1:
            lines += [
                f"  detectors:          {self.detectors}",
                f"  cpiArray:           {self.cpi_array}",
                f"  countInRangeArray:  {self.count_in_range_array}",
                f"  xDirection:         {self.x_direction:g}",
                f"  yDirection:         {self.y_direction:g}",
                f"  zDirection:         {self.z_direction:g}",
            ]
        return "Packet0:\n" + "\n".join(lines)


# Parameter indices (from Appendix C of the v1.2.2 manual)
PARAM_MAJOR_VERSION = 0
PARAM_MINOR_VERSION = 1
PARAM_RELEASE_VERSION = 2
PARAM_DIVISOR = 3
PARAM_PPR = 4
PARAM_TEMP_STAB = 5
PARAM_SPECTRUM_TYPE = 6
PARAM_ENERGY_CORR = 7
PARAM_DETECTOR_INDEX = 8
PARAM_MOVING_SPECTRUM = 9
PARAM_MOVING_DEPTH = 10
PARAM_COMM_INTERVAL = 11
PARAM_PULSE_THRESHOLD = 12
PARAM_DAC = 13
PARAM_RATE_FEEDBACK = 14
PARAM_MIN_CHANNEL = 15
PARAM_MAX_CHANNEL = 16
PARAM_DAC_BUMP = 17


class MCAParameters:
    """Device parameters read from the MCA (128 x int32)."""

    LABELS = {
        0: 'Major version',
        1: 'Minor version',
        2: 'Release version',
        3: 'Divisor for integral to channel',
        4: 'Pulse pileup rejection on/off',
        5: 'Temperature stabilization on/off',
        6: 'Spectrum type (0=count, 1=width, 2=ADC)',
        7: 'Energy correction on/off',
        8: 'Detector index in array',
        9: 'Moving spectrum on/off',
        10: 'Depth of moving spectra [0,32]',
        11: 'Communication interval [1,100]*100ms',
        12: 'Pulse threshold (ADC levels)',
        13: 'DAC [0,4095] (HV when TS off)',
        14: 'Rate feedback (0=cps, 1=DAC)',
        15: 'Min channel for ADC buffer capture',
        16: 'Max channel for ADC buffer capture',
        17: 'One-time DAC bump [-100,100]',
    }

    def __init__(self, data: bytes):
        self.values = list(struct.unpack(f'<{NUM_PARAMS}i', data))

    def __getitem__(self, index):
        return self.values[index]

    def __repr__(self):
        lines = [f"MCA Parameters (firmware {self.values[0]}.{self.values[1]}.{self.values[2]}):"]
        for i in range(min(18, len(self.values))):
            label = self.LABELS.get(i, f'param[{i}]')
            lines.append(f"  [{i:3d}] {self.values[i]:>10d}  {label}")
        return '\n'.join(lines)

    @property
    def firmware_version(self):
        return f"{self.values[0]}.{self.values[1]}.{self.values[2]}"

    @property
    def moving_spectrum_enabled(self):
        return bool(self.values[PARAM_MOVING_SPECTRUM])

    @property
    def moving_depth(self):
        return self.values[PARAM_MOVING_DEPTH]

    @property
    def comm_interval_ms(self):
        return self.values[PARAM_COMM_INTERVAL] * 100


class CapeMCA:
    """Interface to a CapeSym MCA radiation sensor over USB."""

    def __init__(self, device=None):
        self._dev = device
        self._attached = False

    def connect(self):
        """Find and open the MCA device."""
        self._dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if self._dev is None:
            raise ConnectionError(
                f"MCA device not found (VID={VENDOR_ID:#06x}, PID={PRODUCT_ID:#06x}). "
                "Check USB connection and udev rules."
            )

        # On Linux, detach kernel driver if it claimed the interface
        if self._dev.is_kernel_driver_active(0):
            self._dev.detach_kernel_driver(0)
            self._attached = True

        self._dev.set_configuration()
        usb.util.claim_interface(self._dev, 0)

        serial = usb.util.get_string(self._dev, self._dev.iSerialNumber)
        print(f"Connected to MCA: {serial or 'unknown'}")

    def close(self):
        """Release the USB interface and close the device."""
        if self._dev is not None:
            try:
                self._dev.clear_halt(ENDPOINT_IN)
                self._dev.clear_halt(ENDPOINT_OUT)
            except usb.core.USBError:
                pass
            try:
                self._dev.reset()
            except usb.core.USBError:
                pass
            usb.util.release_interface(self._dev, 0)
            if self._attached:
                self._dev.attach_kernel_driver(0)
            usb.util.dispose_resources(self._dev)
            self._dev = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    def _send_command(self, cmd: bytes):
        """Write a 2-byte command to the device."""
        written = self._dev.write(ENDPOINT_OUT, cmd, timeout=TIMEOUT_MS)
        if written != len(cmd):
            raise IOError(f"Write failed: sent {written}/{len(cmd)} bytes")

    def _read_response(self, size: int) -> bytes:
        """Read a response of the expected size from the device."""
        data = self._dev.read(ENDPOINT_IN, size, timeout=TIMEOUT_MS)
        return bytes(data)

    def read_status(self) -> Packet0:
        """Request and return the device status (packet0)."""
        self._send_command(CMD_PACKET0)
        data = self._read_response(PACKET0_SIZE)
        return Packet0(data)

    def read_spectrum(self) -> list[int]:
        """Request and return the energy spectrum (4096 channels)."""
        self._send_command(CMD_SPECTRUM)
        data = self._read_response(SPECTRUM_CHANNELS * 4)
        return list(struct.unpack(f'<{SPECTRUM_CHANNELS}I', data))

    def zero_spectrum(self):
        """Zero out all spectrum channels in the MCA.

        The device echoes [1,1] back as confirmation.
        """
        self._send_command(CMD_ZERO_SPECTRUM)
        reply = self._read_response(2)
        if reply != CMD_ZERO_SPECTRUM:
            raise IOError(
                f"Zero spectrum: unexpected reply {list(reply)}, "
                f"expected {list(CMD_ZERO_SPECTRUM)}"
            )

    def read_parameters(self) -> MCAParameters:
        """Read the 128-element parameter array from the MCA."""
        self._send_command(CMD_READ_PARAMS)
        data = self._read_response(NUM_PARAMS * 4)
        return MCAParameters(data)

    def set_parameter(self, index: int, value: int):
        """Set a single MCA parameter by index (4-32) to value (byte2).

        Only indices 4-32 (excluding 17) are valid for simple assignment.
        Index 17 is the DAC bump command (use bump_dac instead).
        Changes take effect at the next communication interval.
        """
        if not (4 <= index <= 32):
            raise ValueError(f"Parameter index must be 4-32, got {index}")
        if index == 17:
            raise ValueError("Use bump_dac() for index 17 (DAC increment)")
        cmd = bytes([index, value & 0xFF])
        self._send_command(cmd)
        reply = self._read_response(2)
        if reply != cmd:
            raise IOError(
                f"Set parameter: unexpected reply {list(reply)}, "
                f"expected {list(cmd)}"
            )

    def bump_dac(self, increment: int):
        """Increment the DAC level by a signed value [-100, 100]."""
        if not (-100 <= increment <= 100):
            raise ValueError(f"DAC increment must be in [-100, 100], got {increment}")
        cmd = bytes([17, increment & 0xFF])
        self._send_command(cmd)
        reply = self._read_response(2)
        if reply != cmd:
            raise IOError(
                f"Bump DAC: unexpected reply {list(reply)}, "
                f"expected {list(cmd)}"
            )

    def stop(self):
        """Stop the MCA and enter Stop mode.

        In Stop mode, the device accepts 512-byte parameter writes
        and special commands. Send any 2-byte command to restart.
        """
        self._send_command(CMD_STOP)
        reply = self._read_response(2)
        if reply != CMD_STOP:
            raise IOError(
                f"Stop: unexpected reply {list(reply)}, "
                f"expected {list(CMD_STOP)}"
            )

    def start(self):
        """Restart the MCA from Stop mode by sending a 2-byte command.

        Any 2-byte command restarts the run loop; we re-send the stop
        command bytes which will be processed as a run-mode command
        at the next interval. Using CMD_PACKET0 to restart cleanly.
        """
        self._send_command(CMD_PACKET0)

    def decode_channel0(self, spectrum: list[int]) -> tuple[int, float]:
        """Decode channel 0 into (cps, temperature_celsius).

        Channel 0 upper 16 bits = detection events in prior interval,
        lower 16 bits = 16 * temperature in degrees C.
        """
        raw = spectrum[0]
        cps = (raw >> 16) & 0xFFFF
        temp_c = (raw & 0xFFFF) / 16.0
        return cps, temp_c


def find_all_mcas():
    """Return a list of all connected MCA USB devices."""
    devices = list(usb.core.find(
        idVendor=VENDOR_ID, idProduct=PRODUCT_ID, find_all=True
    ))
    return devices


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

    spectra = []
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
        plt.savefig("spectra.png", dpi=150)
        print("Plot saved to spectra.png")
        plt.show()
