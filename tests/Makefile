SIM ?= icarus
TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES += $(PWD)/../hdl/dut.v
VERILOG_SOURCES += $(PWD)/../hdl/dut_wrapper.v
VERILOG_SOURCES += $(PWD)/../hdl/delayed_dut_wrapper.v
VERILOG_SOURCES += $(PWD)/../hdl/FIFO1.v
VERILOG_SOURCES += $(PWD)/../hdl/FIFO2.v

all: or delayed_or
or:
    rm -rf sim_build
    $(MAKE) sim MODULE=dut_test TOPLEVEL=dut_wrapper
delayed_or:
    rm -rf sim_build
    $(MAKE) sim MODULE=dut_test TOPLEVEL=delayed_dut_wrapper

include $(shell cocotb-config --makefiles)/Makefile.sim
