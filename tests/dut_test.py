import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly, NextTimeStep, FallingEdge
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor
import os
import random
from cocotb_coverage.coverage import CoverPoint, CoverCross, coverage_db

# Scoreboard callback function
def sb_fn(actual_value):
    global expected_value
    print(f"[SB] Expected: {expected_value[0]}, Got: {actual_value}")
    assert actual_value == expected_value.pop(0), "Scoreboard matching failed"

@CoverPoint("top.a", xf=lambda x,y:x, bins=[0,1])
@CoverPoint("top.b", xf=lambda x,y:y, bins=[0,1])
@CoverCross("top.cross.ab", items=["top.a","top.b"])
def ab_cover(a,b):
    pass
    
@CoverPoint("top.prot.a.current",xf=lambda x:x["current"], bins=["Idle","Rdy","Txn"])
@CoverPoint("top.prot.a.previous",xf=lambda x:x["previous"], bins=["Idle","Rdy","Txn"])
@CoverCross("top.a_prot.cross",items=["top.prot.a.current","top.prot.a.previous"])
def a_prot_cover(txn):
    pass

# Write driver
class WriteDriver(BusDriver):
    _signals = ["rdy", "en", "data", "address"]

    def __init__(self, dut, name, clk):
        super().__init__(dut, name, clk)
        self.clk = clk
        self.bus.en.value = 0

    async def driver_send(self, value, address):
        await RisingEdge(self.clk)
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
        await RisingEdge(self.clk)
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

class IO_Monitor(BusMonitor):
    _signals=["rdy","en","data"]
    async def _monitor_recv(self):
        fallingedge=FallingEdge(self.clock)
        rdonly=ReadOnly()
        phases={0:"Idle",1:"Rdy",3:"Txn"}
        prev="Idle"
        while True:
            await fallingedge
            await rdonly
            txn=(self.bus.en.value<<1)|(self.bus.rdy.value)
            current=phases[txn]
            data={"previous":prev,"current":current}
            self._recv(data)
            prev=current

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
    #defining input values
    global expected_value
    a = [0, 0, 1, 1]
    b = [0, 1, 0, 1]
    expected_value = [0, 1, 1, 1]  # Expected Y outputs only

    # Reset sequence
    dut.RST_N.value = 1
    await Timer(1, "ns")
    dut.RST_N.value = 0
    await Timer(1, "ns")
    await RisingEdge(dut.CLK)
    dut.RST_N.value = 1

    # Instantiate drivers
    write_driver = WriteDriver(dut, "write", dut.CLK)
    read_driver = ReadDriver(dut, "read", dut.CLK, sb_fn)
    IO_Monitor(dut,"write",dut.CLK, callback=a_prot_cover)

    for i in range(4):
        print(f"\n[TEST] ===== Iteration {i} =====")
        # Wait and write to A
        await wait_for_status(read_driver, 0)  # A_Status
        await write_driver.driver_send(a[i], address=4)

        # Wait and write to B
        await wait_for_status(read_driver, 1)  # B_Status
        await write_driver.driver_send(b[i], address=5)

        ab_cover(a[i],b[i])

        # Wait and read Y output
        await wait_for_status(read_driver, 2)  # Y_Status
        await read_driver.driver_send(address=3, verify=True)

        # Small delay between iterations
        await Timer(2, "ns")
    coverage_db.report_coverage(cocotb.log.info, bins = True)
    coverage_file=os.path.join(os.getenv("RESULT_PATH","./"),"coverage.xml")
    coverage_db.export_to_xml(filename=coverage_file)


        
    
