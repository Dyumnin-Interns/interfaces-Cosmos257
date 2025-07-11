import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly, NextTimeStep
from cocotb_bus.drivers import BusDriver

# Scoreboard callback function
def sb_fn(actual_value):
    global expected_value
    print(f"[SB] Expected: {expected_value[0]}, Got: {actual_value}")
    assert actual_value == expected_value.pop(0), "Scoreboard matching failed"

# Write driver
class WriteDriver(BusDriver):
    _signals = ["rdy", "en", "data", "address"]

    def __init__(self, dut, name, clk):
        super().__init__(dut, name, clk)
        self.clk = clk
        self.bus.en.value = 0

    async def driver_send(self, value, address):
        if self.bus.rdy.value != 1:
            print(f"[WRITE] Waiting for rdy=1 at addr={address}")
            await RisingEdge(self.bus.rdy)
        print(f"[WRITE] Writing value={value} to address={address}")
        self.bus.en.value = 1
        self.bus.data.value = value
        self.bus.address.value = address
        await ReadOnly()
        await RisingEdge(self.clk)
        self.bus.en.value = 0
        await NextTimeStep()

# Read driver
class ReadDriver(BusDriver):
    _signals = ["rdy", "en", "data", "address"]

    def __init__(self, dut, name, clk, sb_callback):
        super().__init__(dut, name, clk)
        self.clk = clk
        self.bus.en.value = 0
        self.callback = sb_callback

    async def driver_send(self, address, verify=False):
        if self.bus.rdy.value != 1:
            print(f"[READ] Waiting for rdy=1 at addr={address}")
            await RisingEdge(self.bus.rdy)
        print(f"[READ] Reading from address={address}")
        self.bus.en.value = 1
        self.bus.address.value = address
        await ReadOnly()
        data_val = self.bus.data.value.integer
        print(f"[READ] Got data={data_val} from address={address}")
        if verify:
            self.callback(data_val)
        await RisingEdge(self.clk)
        self.bus.en.value = 0
        await NextTimeStep()
        return data_val

# Helper function to poll a status register until it returns 1
async def wait_for_status(read_driver, status_addr):
    status = 0
    attempts = 0
    while status != 1:
        status = await read_driver.driver_send(address=status_addr, verify=False)
        print(f"[WAIT] Status[{status_addr}] = {status}")
        await Timer(1, "ns")
        attempts += 1
        if attempts > 50:
            raise TimeoutError(f"Timeout waiting for status=1 at address {status_addr}")

# Main test
@cocotb.test()
async def dut_test(dut):
    global expected_value
    a = [0, 0, 1, 1]
    b = [0, 1, 0, 1]
    expected_value = [0, 1, 1, 1]  # Expected Y outputs only

    # Reset DUT
    dut.RST_N.value = 1
    await Timer(1, "ns")
    dut.RST_N.value = 0
    await Timer(1, "ns")
    await RisingEdge(dut.CLK)
    dut.RST_N.value = 1
    print("[TEST] Reset done.")

    # Instantiate drivers
    write_driver = WriteDriver(dut, "write", dut.CLK)
    read_driver = ReadDriver(dut, "read", dut.CLK, sb_fn)

    for i in range(4):
        print(f"\n[TEST] ===== Iteration {i} =====")
        # Wait and write to A
        await wait_for_status(read_driver, 0)  # A_Status
        await write_driver.driver_send(a[i], address=4)

        # Wait and write to B
        await wait_for_status(read_driver, 1)  # B_Status
        await write_driver.driver_send(b[i], address=5)

        # Wait and read Y output
        await wait_for_status(read_driver, 2)  # Y_Status
        await read_driver.driver_send(address=3, verify=True)

        # Small delay between iterations
        await Timer(2, "ns")


        
    
