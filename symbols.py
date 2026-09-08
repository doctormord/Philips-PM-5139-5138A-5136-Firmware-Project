"""PM5139 symbol table — evidence only.

Based on the sections of PM5139_Hardware_Reference.md. Everything here is
either traced in the listing, measured in the emulator or documented in the
service manual. Assumptions are marked with a question mark and belong in
the comment, never in a name.
"""

# ---------------------------------------------------------------- Routines
# address -> (short name, description, section)
ROUTINES = {
    0x0006: ("MAIN_LOOP",      "main loop entry, clears accumulator and PSW", None),
    0x031F: ("KEY_DIALLOCK",   "handler DIAL LOCK: toggles 2Eh.4. Inline as the 16th entry "
                               "of jump table 0301h", 25),
    0x0227: ("KEY_DECODER",    "decodes the SAA3007 word from P3.3", 11),
    0x0805: ("PARAM_DIGIT",    "fetches one digit of the parameter", 21),
    0x080B: ("PARAM_LOAD",     "loads the selected parameter into 15h..19h, R4 = target", 21),
    0x09AF: ("OUT_DC_AMPL",    "fixed setting to STR7 and STR9", 22),
    0x09BF: ("OUT_FREQ",       "computes the frequency and sends it to the TWS", 18),
    0x09E5: ("FREQ_EXPONENT",  "ORs the decade index from table 09EAh into 12h", 18),
    0x0A26: ("FREQ_BCD2BIN",   "frequency 50h..52h from BCD to binary, 24 bit", 18),
    0x0A90: ("OFFSET_CALC",    "computes the DC component", 22),
    0x0AAC: ("AMPL_CALC",      "computes the amplitude", 20),
    0x0B57: ("AMPL_CORRECT",   "amplitude correction per waveform", 20),
    0x0E54: ("SEND_STR6",      "four bytes from 11h..14h to the TWS, unit 2 D331", 4),
    0x0E5B: ("SEND_STR7",      "two bytes to the DC generator, unit 3 D301", 4),
    0x0E62: ("SEND_STR9",      "one byte to the amplitude controller, unit 3", 4),
    0x0E69: ("SEND_STR5",      "to the modulation oscillator, unit 4: six bytes "
                               "14h,13h,12h,11h,19h,18h. Chain SD1 -> D139 -> D138 "
                               "-> D130. 11h..14h = TWS frequency word, 19h = DAC "
                               "N135, 18h = multiplexer D140/D141", 30),
    0x0E78: ("SEND_STR3",      "to the amplitude modulator and pulse generator, unit 4", 4),
    0x0E7F: ("SEND_STR4",      "to the burst logic, unit 4", 4),
    0x0E8A: ("SEND_BYTES",     "sends R4 bytes from RAM at R0 downwards through SBUF", 3),
    0x0E98: ("STROBE_FIRE",    "ORs DPH with 80h, MOVX, then returns to the idle output", 3),
    0x1032: ("BITS_REVERSE",   "reverses the bit order in the accumulator, ACC.0 against ACC.7 "
                               "and so on; prepares data for the shift registers, then STR9", 4),
    0x2157: ("TAB_ACCESS_2200","helper for the table access at 2200h in the arithmetic "
                               "library; computes in X", 24),
    0x3029: ("X_TIMES_BYTE",   "multiplies X by the byte in R6, carry into R3", 24),
    0x4EBE: ("POINTER_CHECK",  "checks which parameter the digit pointer 0Bh selects; "
                               "five entry points from the user interface", 21),
    0xAC47: ("VERSION_DISPLAY","shows the firmware version at power-up: 3Fh = first "
                               "cell with separator, 40h = second, then DISPLAY_SEND. "
                               "V1.3 sets 0Eh/3Dh = \"1.3\", V1.5 0Eh/B5h = \"1.5\". "
                               "Runs inside the reset sequence at 3AA8h", 34),
    0x59D1: ("TEST_MENU",      "menu of the diagnostic program; jump table 5A0Bh", 7),
    0x5A0B: ("TAB_SELFTEST",   "eight LJMP entries pointing at the test programs", 7),
    0x5A2F: ("TEST1_DISPLAY",  "self-test 1: Display Test", 7),
    0x5A42: ("TEST2_KEYBOARD", "self-test 2: Keyboard Test", 7),
    0x5ADB: ("TEST3_MEMORY",   "self-test 3: Memory Register Test", 7),
    0x5B44: ("TEST4_STROBE",   "self-test 4: Strobe Test", 7),
    0x5C0B: ("TEST5_IFACE",    "self-test 5: Interface Test, RS-232 or IEEE-488", 7),
    0x5D68: ("TEST6_KNOB",     "self-test 6: Rotary Knob Test", 7),
    0x5EE9: ("TEST7_EEPROM",   "self-test 7: EEPROM Test", 7),
    0x3DAB: ("LOAD_SINE",      "waveform table 44A7h into the waveform RAM through STR2", 6),
    0x3EFC: ("LOAD_HAVERSINE", "waveform table 46A9h into the waveform RAM, 512 x 12 bit", 6),
    0x4003: ("LOAD_SINE_B",    "second path for table 44A7h", 6),
    0x4425: ("LOAD_LEVEL_SERIES","waveform table 4AABh into the waveform RAM: ten sine arcs "
                               "with logarithmically falling amplitude, 3.33 dB per step", 6),
    0x9E37: ("LOAD_ARB_ROM",   "one of the three built-in curves A047h/A447h/A847h, "
                               "selected through RAM 0Dh", 6),
    0x645A: ("ERROR_REPORT",   "A = error number: stored in 49h, class mask from "
                               "table 6465h (56 bytes) ORed into 69h, 24h.3 set", 32),
    0x649D: ("ERROR_SELECT",   "picks the error number matching the operating mode and "
                               "reports it through 64BBh to ERROR_REPORT", 32),
    0x6A85: ("CMD_DISPATCH",   "command code in 10h: upper nibble 60h -> 8871h, C0h -> 6B51h, "
                               "otherwise the shared interpreter 71BFh", 32),
    0x6B51: ("CMD_C0",         "execution part of command group C0h: the IEEE-488.2 "
                               "common commands *CLS *ESE *ESR *OPC *RST *SRE *STB "
                               "*TST *WAI", 32),
    0x6CEC: ("TAB_LRN",        "50 bytes: which command tokens describe the setting per "
                               "operating mode, eight groups separated by 00h, ordered "
                               "like the one-hot byte 2Ch. Basis of the learn query *LRN?", 32),
    0x6D1E: ("REPLY_BUILD",    "assembles the remote control reply texts in the buffer at 4Fh; "
                               "uses MSG_APPEND and table 6CECh", 32),
    0x7415: ("ARG_PARSE",      "parses the argument of a command, called from 6B51h (group C0h) "
                               "and 71C7h; carry signals failure", 32),
    0x7693: ("ARG_NUMBER",     "numeric part of the argument into Y, reports range errors "
                               "through ERROR_REPORT", 32),
    0x71BF: ("CMD_INTERPRET",  "shared command interpreter for keyboard and remote "
                               "control, table 7752h", 16),
    0x7752: ("TAB_COMMANDS",   "131 entries of 16 bytes: 14 bytes name, then token with "
                               "parameter and token alone. See PM5139_Tables.md", 16),
    0x8014: ("MSG_APPEND",     "appends the message with index R4 from pointer table 803Ch "
                               "to the buffer at 4Fh", 16),
    0x803C: ("TAB_MESSAGES",   "124 pointers, 16 bit big endian, to length-prefixed "
                               "texts. See PM5139_Tables.md", 16),
    0x8871: ("CMD_60",         "entry of command group 60h from dispatcher 6A91h: the arbitrary "
                               "commands ARB ARBSELECT ARBITEXECUTE ARON AROFF CLARB "
                               "BEGIN COUNT DATA FILL. Largest contiguous block "
                               "of the ROM", 32),
    0x8A1C: ("ARB_PART_8A1C",  "second large execution part of group 60h, from 6804h "
                               "and three places inside the block; computes in Z and Y, "
                               "reports errors through 645Ah", 32),
    0x8CB9: ("ARB_PART_8CB9",  "from 63FDh; stores 34h/35h in the upper RAM buffer at FBh..FDh "
                               "and works with 4Bh/4Ch, the interface pointers", 32),
    0x8DE3: ("ARB_HELPER_8DE3","short helper without calls of its own, from 6B4Dh and five "
                               "places inside the block", 32),
    0x8E1C: ("ARB_HELPER_8E1C","22 bytes, from 6EC5h; calls 8E11h and 8DE3h", 32),
    0x8E32: ("ARB_HELPER_8E32","35 bytes, from 3CEDh in the initialisation", 32),
    0x8E55: ("ARB_PART_8E55",  "from 6896h; display cells 32h/33h/3Eh, reads the "
                               "status register", 32),
    0x8F03: ("ARB_PART_8F03",  "largest sub-area, from 68A2h and four places inside the block; "
                               "builds the display, reads the status register, uses the "
                               "interface pointer 4Ch", 32),
    0x932A: ("ARB_PART_932A",  "from 687Ah; status register, interface pointers 4Bh/4Ch "
                               "and the arithmetic registers X", 32),
    0x97D9: ("ARB_OUTPUT",     "output sequence with fixed constants through 43ADh and 10B5h, "
                               "from 3B74h, 3D08h and four places inside the block", 32),
    0x98B3: ("ARB_PART_98B3",  "from 5F01h and 966Bh; sets Y to 0200h and masks, "
                               "uses the curve number 67h", 32),
    0x9615: ("ARB_DIR_CHECK",  "checks the arbitrary EEPROM directory: header 0000h = count "
                               "in the lower nibble, 0001h = check byte over n*5+5 bytes from "
                               "0002h, start value 55h + header byte. On failure 22h.7", 32),
    0x991F: ("ARB_RECORD_LOAD","four data bytes of the selected curve record into X1..X4: "
                               "EEPROM from 0003h + k*5, k from the upper nibble of 67h; "
                               "with 20h.1 set from the RAM buffer at E0h instead", 32),
    0x0F69: ("MOD_CTRL_BYTE",  "builds 18h from the operating mode: one-hot 2Ch -> bit number, "
                               "+8 if 2Fh.5 or 2Fh.4, table at 0F83h; bit 1 from "
                               "29h.7 AND 2Ch.2. Goes to D139 as the sixth STR5 byte", 30),
    0x08EA: ("PARAM_ADDRESS",  "R0 = RAM address of the selected parameter from "
                               "table 08F2h, index 24h & 0Fh; R2 = decade", 33),
    0x08F2: ("TAB_PARAM_ADDR", "50 53 56 58 5A 5C 5E 60 62 64 66 68 67 6A 67 - "
                               "RAM address per parameter index", 33),
    0x0663: ("PARAM_CHECK",    "handler: loads the parameter, fetches the flag byte from 069Dh, "
                               "and on bit 7 or 6 checks the limit through 1121h", 33),
    0x069D: ("TAB_PARAM_FLAGS","flag byte per parameter index; bit 7 or 6 means "
                               "limit-checked", 33),
    0x11CC: ("PARAM_LIMIT",    "checks the upper limit of the parameter: R3 = (24h&0Fh - 1)*2, "
                               "limit from 12D2h into Z3/Z4, then COMPARE_YZ. "
                               "Carry set = value rejected", 33),
    0x12D2: ("TAB_PARAM_LIMITS","12 upper limits as BCD, indexed by parameter: 2001 201 "
                               "21 11 11 11 21 101 201 19 10 101. In V1.5 at 134Fh", 33),
    0x14B2: ("SWEEP_SETUP",    "prepares the sweep: time, limits, direction, step sizes", 23),
    0x15FC: ("NORMALIZE",      "shifts Y so that 15h lies in 08h..0Fh; R7 = exponent", 24),
    0x162C: ("SWEEP_F_BCD2BIN","fSTART or fSTOP to binary, unit 0.1 Hz. "
                               "22h.4 selects between them. Truncates the mantissa to 16 bit", 23),
    0x1907: ("SWEEP_START",    "clears the accumulators and step counter, starts timer 1", 23),
    0x1932: ("SWEEP_LOOP",     "one sweep step: count, ramp, frequency, output", 23),
    0x1CBA: ("TWS_SEND",       "four bytes from 14h downwards to the TWS", 23),
    0x1CD9: ("SWEEP_STEP",     "telegrams of the step, then waits for timer 1", 23),
    0x1D38: ("MANTISSA_X2",    "shifts 11h..14h left by one bit: N = 2*M of the TWS", 18),
    0x1D4E: ("SWEEP_ROUND",    "adds the rounding carry from R6.7 onto 12h..14h", 23),
    0x1D62: ("RAM_PAGE",       "builds F0h/F1h for STR1, page select of the waveform RAM", 23),
    0x1D8E: ("SWEEP_RESCALE",  "rescales the accumulator, table 2019h, then adds fSTART", 23),
    0x1E5C: ("SWEEP_LOG_EXP",  "logarithmic branch: exponent and fractional part", 23),
    0x1F40: ("BIT_SHIFT",      "shifts Y by R5 bits, encoding see section 23", 23),
    0x2398: ("TAB_POW2",       "257 entries: round((2^(i/256)-1)*65536), for exp and log", 23),
    0x2019: ("TAB_RESCALE",    "40 shift codes, index 25h minus 1Fh", 23),
    0x2041: ("TWS_DECADE",     "determines the decade of the TWS word, result in R7", 23),
    0x2218: ("POWER_OF_TWO",   "X = W * 2^((13h+14h/256)/256) * 65536; table 2398h, "
                               "linearly interpolated", 23),
    0x2323: ("LOGARITHM",      "searches table 2398h backwards: index and remainder = logarithm", 23),
    0x25C2: ("KNOB_QUADRATURE","counts detents; F0 holds the direction of rotation", 19),
    0x25F6: ("KNOB_EVALUATE",  "turns the detent count into a step size", 21),
    0x2622: ("TAB_ACCEL",      "acceleration, up to 15 detents", 21),
    0x260E: ("TAB_ACCEL2",     "acceleration from 16 detents on", 21),
    0x26AB: ("TAB_WEIGHTS",    "weight per digit position", 19),
    0x2724: ("TAB_INCREMENT",  "32 BCD increments, geometric from 1 to 5000", 19),
    0x2764: ("INCREMENT_ADD",  "adds increment 1Ch..1Eh onto 17h..19h; F0=0 adds, F0=1 subtracts", 19),
    0x27D9: ("TRIAL_SUBTRACT", "subtraction on trial first; 22h.6 = zero, 22h.7 = underflow", 19),
    0x29C9: ("RANGE_CHECK",    "range check, jump table 29DBh by parameter", 19),
    0x2A16: ("FREQ_RANGE",     "frequency limits; table 2A81h, clamps at 0Bh=11h to 20000", 19),
    0x2A81: ("TAB_FREQ_LIMITS","limit per decade, stored halved", 19),
    0x2EA1: ("NVRAM_MARK",     "check mark of a memory record: byte sum from RAM 30h with "
                               "start value AAh over 25 bytes, over 24 when an arbitrary "
                               "curve is selected", 26),
    0x2F51: ("NVRAM_ADDR_READ","device address from NVRAM FEh/FFh; the mark is value+55h, "
                               "checked by XOR, otherwise default 20h", 26),
    0x2FA0: ("MUL_XYZ",        "X = Y * Z, 40 bit without loss", 24),
    0x3107: ("DIV_XYZ",        "X = Y / Z, integer, rounded down", 24),
    0x31C7: ("COMPARE_YZ",     "compares Y against Z", 24),
    0x31D7: ("COMPARE_5",      "five bytes @R0 minus @R1, result in the carry", 24),
    0x31E4: ("CLEAR_XYZ",      "clears X, Y and Z, 15 bytes from 10h", 24),
    0x31EE: ("CLEAR_X",        "clears X", 24),
    0x31F2: ("CLEAR_Y",        "clears Y", 24),
    0x31F6: ("CLEAR_Z",        "clears Z", 24),
    0x3202: ("X_TO_Z",         "moves X to Z, clearing the source", 24),
    0x3206: ("X_TO_Y",         "moves X to Y, clearing the source", 24),
    0x3236: ("Y_RIGHT",        "shifts Y right by one bit", 24),
    0x324E: ("X_LEFT",         "shifts X left by one bit", 24),
    0x3252: ("Y_LEFT",         "shifts Y left by one bit", 24),
    0x3256: ("Z_LEFT",         "shifts Z left by one bit", 24),
    0x326B: ("NIBBLE_LEFT",    "shifts five bytes left by one nibble, BCD times ten", 24),
    0x32AE: ("Y_MINUS_Z_ABS",  "Y = |Y - Z|; carry set if Z was larger", 24),
    0x32DB: ("BIN2BCD",        "binary to BCD, digits accumulated in 14h", 24),
    0x3313: ("BCD2BIN",        "six BCD digits from 17h..19h to binary in 12h..14h", 24),
    0x3338: ("BIT_LENGTH",     "bit length of a five-byte value into R4", 24),
    0x3381: ("DISPLAY_BUILD",  "builds the display buffer 30h..43h from the device state", 15),
    0x37DB: ("DISPLAY_SEND",   "sends the display buffer over I2C to the PCF8576 (70h)", 14),
    0x392F: ("DISPLAY_SEND2",  "second path to the display", 14),
    0x3A9A: ("RESET",          "reset entry point", 1),
    0x3AAB: ("CHECKSUM",       "forms the ROM checksum and compares it against AC70h", 1),
    0x517D: ("STATUS_READ",    "reads the status register through STR0", 5),
    0x5187: ("I2C_START_W",    "start condition, address in A with R/W=0", 28),
    0x5194: ("I2C_START_R",    "start condition, address in A with R/W=1", 28),
    0x51A1: ("I2C_BYTE",       "sends one byte, MSB first; ACK ends up in the carry", 28),
    0x51C1: ("I2C_STOP",       "stop condition", 28),
    0x5F2E: ("IFACE_HANDLER",  "services the interface card: read, otherwise re-register", 28),
    0x5F74: ("IFACE_SEARCH",   "searches for the card; an ACK sets 25h.7", 28),
    0x5FA9: ("IFACE_RECEIVE",  "reads the status byte, the data block and the checksum", 28),
    0x614A: ("IFACE_START_W",  "checks the bus, then start at 5Eh for writing", 28),
    0x6158: ("IFACE_START_R",  "checks the bus, then start at 5Eh for reading", 28),
    0x6166: ("IFACE_ADDRESS",  "sends the device address as E0h/E1h and C0h", 28),
    0x6180: ("IFACE_STATUSCMD","sends status command 80h with the state bits", 28),
    0x61A2: ("IFACE_COMMAND",  "sends one command byte from R5 and terminates", 28),
    0x61E8: ("IFACE_ADDR_BCD", "device address from 68h, BCD to binary; gone in V1.5", 28),
    0x6130: ("IFACE_LOCREM",   "control byte E2h = LOCAL, E3h = REMOTE; sets 26h.1", 28),
    0x666A: ("REMOTE_SWITCH",  "checks the status register and sets or clears 2Eh.3", 28),
    0x0EA1: ("IFACE_ENABLE",   "device address 31 enables reception through 25h.0", 28),
    0x6244: ("IFACE_BYTE_STOP","sends a byte, then stop", 28),
    0x625A: ("I2C_RELEASE",    "releases the bus and sends stop", 28),
    0xAC54: ("IDENT_STRING",   "length byte 1Ah, then PHILIPS,PM5139,0,V1.3/0000", 28),
    0xAC70: ("ROM_CHECKSUM",   "checksum of the ROM", 1),
}

# -------------------------------------------------------------- RAM symbols
# address -> (name, explanation)
RAM = {
    0x0B: ("DIGIT_POINTER", "R3 of bank 1: selected digit position while editing"),
    0x10: ("X0", "arithmetic register X, most significant"),
    0x11: ("X1", "X / TWS telegram: command code"),
    0x12: ("X2", "X / TWS telegram: exponent in bits 5..7"),
    0x13: ("X3", "X / TWS telegram: N, high part"),
    0x14: ("X4", "X / TWS telegram: N, low part"),
    0x15: ("Y0", "arithmetic register Y, most significant; the frequency accumulator in a sweep"),
    0x16: ("Y1", "Y"), 0x17: ("Y2", "Y"),
    0x18: ("Y3", "Y / STR5 telegram: control byte for D139, multiplexer D140/D141"),
    0x19: ("Y4", "Y, least significant / STR5 telegram: DAC value for D138, N135"),
    0x1A: ("Z0", "arithmetic register Z, most significant; the step size in a sweep"),
    0x1B: ("Z1", "Z"), 0x1C: ("Z2", "Z"), 0x1D: ("Z3", "Z"), 0x1E: ("Z4", "Z, least significant"),
    0x1F: ("EXPONENT", "normalisation exponent from 15FCh"),
    0x35: ("RAMP_STEP", "step size of the sweep ramp, 32 bit from here"),
    0x39: ("RAMP_ACC", "ramp accumulator; this byte goes to STR8"),
    0x3D: ("SWEEP_N", "number of sweep steps, 24 bit from here"),
    0x40: ("SWEEP_COUNTER", "step counter of the sweep, 24 bit from here"),
    0x43: ("RETRACE_TIME", "retrace pause after the sweep: 43h overflows, 44h:45h timer start"),
    0x49: ("ERROR_NUMBER", "error number last reported, set by 645Ah"),
    0x67: ("ARB_CURVE", "upper nibble: selected arbitrary curve k; 9650h resets it to 1"),
    0x69: ("ERROR_CLASS", "collected mask of the error classes, ORed by 645Ah"),
    0x4A: ("IFACE_COUNTER", "interface: remaining count"),
    0x4B: ("IFACE_STATUS", "interface: length and status bits"),
    0x4C: ("IFACE_POINTER", "interface: write pointer into the receive buffer"),
    0x50: ("FREQ", "frequency: decade in the upper nibble, then five BCD digits"),
    0x53: ("FREQ_STOP", "stop frequency of the sweep, same format"),
    0x56: ("AMPLITUDE", "AC amplitude"),
    0x58: ("OFFSET", "DC component"),
    0x60: ("SWEEP_TIME", "sweep time: range in 60h, two BCD digits in 61h"),
    0x68: ("DEVICE_ADDR", "device address of the interface; BCD in V1.3, binary in V1.5"),
    0x6A: ("SWEEP_CTRL", "sweep control: bit 4 direction, bit 5 sign, bit 6 start-up"),
    0xF0: ("PAGE_LO", "page select of the waveform RAM, low part"),
    0xF1: ("PAGE_HI", "page select of the waveform RAM, high part"),
}

# Ranges that carry a meaning as a block: (from, to, text)
RAM_RANGES = [
    (0x08, 0x0F, "register bank 1"),
    (0x20, 0x2F, "bit-addressable state flags"),
    (0x30, 0x43, "display buffer (partly reused during a sweep)"),
    (0x30, 0x34, "during a sweep: fSTART in binary, unit 0.1 Hz"),
    (0x80, 0xBF, "receive buffer of the interface, 64 bytes"),
]

# -------------------------------------------------------------- bit symbols
# "20h.7" -> (name, evidence)
BITS = {
    "20h.7": ("SWEEP_RUNNING", "set at 14A1h; triggers the sweep, measured"),
    "22h.4": ("AUX_FLAG_A",    "working flag used in many places, e.g. the fSTOP choice in 162Ch"),
    "25h.7": ("IFACE_PRESENT", "the interface card has answered on its address"),
    "26h.1": ("IFACE_REMOTE",  "remote mode; prerequisite for the receive path"),
    "2Ah.0": ("WF_DC",         "waveform DC"),
    "2Ah.1": ("WF_SINE",       "waveform sine"),
    "2Ah.2": ("WF_TRIANGLE",   "waveform triangle"),
    "2Ah.3": ("WF_SQUARE",     "waveform square"),
    "2Ah.4": ("WF_PULSE_POS",  "waveform positive pulse"),
    "2Ah.5": ("WF_PULSE_NEG",  "waveform negative pulse"),
    "2Ah.6": ("WF_SAW_POS",    "waveform rising sawtooth"),
    "2Ah.7": ("WF_SAW_NEG",    "waveform falling sawtooth"),
    "2Bh.1": ("WF_HAVERSINE",  "waveform haversine"),
    "2Bh.2": ("WF_SINE_PULSE", "waveform sine pulse"),
    "2Bh.3": ("WF_TRIANGLE_PULSE", "waveform triangle pulse"),
    "2Bh.4": ("WF_ARBITRARY",  "waveform arbitrary"),
    "2Ch.0": ("MOD_OFF",       "modulation off"),
    "2Ch.1": ("MOD_AM",        "amplitude modulation"),
    "2Ch.2": ("MOD_FM",        "frequency modulation"),
    "2Ch.3": ("MOD_PSK",       "PSK"),
    "2Ch.4": ("MOD_GATE",      "gate"),
    "2Ch.5": ("SWEEP_LIN",     "sweep linear"),
    "2Ch.6": ("SWEEP_LOG",     "sweep logarithmic"),
    "22h.7": ("ARB_REJECTED",  "the arbitrary EEPROM directory failed its checksum"),
    "24h.3": ("ERROR_PENDING", "an error has been reported, number in 49h"),
    "2Ch.7": ("MOD_BURST",     "burst"),
    "2Eh.3": ("REMOTE",        "remote mode, entry 0026h to 62AFh"),
    "2Eh.4": ("DIAL_LOCK",     "rotary knob locked; display DIAL LOCKED through 35h.3"),
    "2Fh.3": ("TRIG_CONT",     "trigger mode CONT or SING"),
    "2Fh.4": ("TRIG_EXT",      "trigger source external"),
    "2Fh.5": ("MODSRC_EXT",    "modulation source external"),
}

# ------------------------------------------------------------------ strobes
STROBES = {
    0x80: "STR0, idle output resp. status register",
    0x81: "STR1, waveform RAM unit 4 D101",
    0x82: "STR2, waveform RAM unit 4 D102/D103",
    0x83: "STR3, amplitude modulator D144 and pulse generator D126",
    0x84: "STR4, burst logic unit 4 D121/D122",
    0x85: "STR5, modulation oscillator unit 4",
    0x86: "STR6, TWS unit 2 D331",
    0x87: "STR7, DC generator unit 3 D301",
    0x88: "STR8, sweep output voltage unit 1 D307",
    0x89: "STR9, amplitude controller unit 3",
}

# I2C addresses
I2C = {0x70: "PCF8576, display", 0xA0: "PCF8570, NVRAM", 0x5E: "interface card"}
