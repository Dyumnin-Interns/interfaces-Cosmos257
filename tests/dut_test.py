import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly, NextTimeStep
from cocotb_bus.drivers import BusDriver

def sb_fn(actual_value):
    global expected_value
    assert actual_value==expected_value.pop(0),"Scoreboard matching failed"
    
class WriteDriver(BusDriver):
    _signals=["rdy", "en", "data", "address"]
    def __init__(self,dut,name,clk):
        BusDriver.__init__(self,dut,name,clk)
        self.clk=clk
        self.bus.en.value=0
    async def driver_send(self,value,address,sync=True):
        if self.bus.rdy.value!=1:
            await RisingEdge(self.bus.rdy)
        self.bus.en.value=1
        self.bus.data.value=value
        self.bus.address.value=address
        await ReadOnly()
        await RisingEdge(self.clk)
        self.bus.en.value=0
        await NextTimeStep()  
    
class ReadDriver(BusDriver):
    _signals=["rdy", "en", "data", "address"]
    def __init__(self,dut,name,clk,sb_callback):
        BusDriver.__init__(self,dut,name,clk)
        self.clk=clk
        self.bus.en.value=0
        self.callback=sb_callback
    async def driver_send(self,address,sync=True):
        if self.bus.rdy.value!=1:
            await RisingEdge(self.bus.rdy)
        self.bus.en.value=1
        await ReadOnly()
        data_val=self.bus.data.value
        self.callback(data_val)
        await RisingEdge(self.clk)
        self.bus.en.value=0
        await NextTimeStep()

@cocotb.test()
async def dut_test(dut):
    global expected_value
    a=[0,0,1,1]
    b=[0,1,0,1]
    expected_value=[0,1,1,1]
    dut.RST_N.value=1
    await Timer(1,"ns")
    dut.RST_N.value=0
    await Timer(1,"ns")
    await RisingEdge(dut.CLK)
    dut.RST_N.value=1
    write_driver=WriteDriver(dut,"write",dut.CLK)
    read_driver=ReadDriver(dut,"read",dut.CLK, sb_fn)
    
    for i in range(4):
        write_driver.driver_send(a[i], address=4)
        write_driver.driver_send(b[i], address=5)
        await Timer(2,"ns")
        read_driver.driver_send(address=3)
    while len(expected_value)>0:
        await Timer(2,"ns")
        
    
