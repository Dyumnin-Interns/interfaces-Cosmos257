import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly, NextTimeStep
from cocotb_bus.drivers import BusDriver
from cocotb.bus.monitors import BusMonitor
from cocotb_coverage.coverage import CoverCross, CoverPoint, coverage_db
import os

class InputDriver(BusDriver):
    _signals=["write_address", "write_data", "write_enable"]
    def __init__(self,dut,name,clk):
        BusDriver.__init__(self,dut,name,clk)
        self.clk=clk
        self.bus.en.value=0
        async def driver_send(self,value,sync=True):
            if self.bus.rdy.value!=1:
                await RisingEdge(self.bus.rdy)
            self.bus.en.value=1
            self.bus.data.value=value
            await ReadOnly()
            await RisingEdge(self.clk)
            self.bus.en=0
            await NextTimeStep()

@cocotb.test()
async def dut_test(dut):
    assert 0, "Test not Implemented"
