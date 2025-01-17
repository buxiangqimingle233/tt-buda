import pybuda
import torch
import os
from pybuda.op.eval.common import op_model_to_desc

# Sample PyTorch module
class PyTorchTestModule(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weights1 = torch.nn.Parameter(torch.rand(32, 128), requires_grad=True)
        self.weights2 = torch.nn.Parameter(torch.rand(32, 128), requires_grad=True)
    def forward(self, act1, act2):
        m1 = torch.matmul(act1, self.weights1)
        m2 = torch.matmul(act2, self.weights2)
        return m1 + m2


def test_module_direct_pytorch():
    input1 = torch.rand(4, 128, 32)
    input2 = torch.rand(4, 128, 32)

    # Set PyBuda configurations
    compiler_cfg = pybuda.config._get_global_compiler_config()
    compiler_cfg.default_df_override = pybuda._C.DataFormat.Float16_b
    compiler_cfg.default_dram_parameters = False
    compiler_cfg.balancer_policy = "Ribbon"
    os.environ["PYBUDA_RIBBON2"] = "1"
    os.environ["TT_BACKEND_OVERLAY_MAX_EXTRA_BLOB_SIZE"] = f"{81*1024}"

    tt0 = pybuda.TTDevice(
        name="tt_device_0",  # here we can give our device any name we wish, for tracking purposes
        arch=pybuda.BackendDevice.Wormhole_B0,  # we set the target device architecture to compile for
        devtype=pybuda.BackendType.Golden  # we set the target backend type to be Golden for running off device
    )

    # Create module
    pybuda_module = pybuda.PyTorchModule("direct_pt", PyTorchTestModule())

    # Place module on device
    tt0.place_module(module=pybuda_module)
    # tt0.compile_for([input1, input2], compiler_cfg=compiler_cfg)
    
    # print(tt0.generate_graph(input1, input2))

    # Push inputs
    tt0.push_to_inputs(input1, input2)
    pybuda.initialize_pipeline(training=False)
    lowered_graph = tt0._compile_output.lowered_graph
    print(lowered_graph.nodes())

    # for op_name, op_model in tt0._compile_output.pass_specific_output_kwargs["balancer_solution"].op_models.items():
        # pass
        # print(str(op_model.op_type))
        # model_desc = op_model_to_desc("matmul", "wormhole", op_model)
    
    # print(len(tt0._compile_output.pass_specific_output_kwargs["balancer_solution"].op_models.values()))
    # print(tt0._compile_output)
    
    pybuda.shutdown()
    
    # output_q = pybuda.run_inference()  # executes compilation (if first time) + runtime
    # output = output_q.get()  # get last value from output queue
    # print(output)


if __name__ == "__main__":
    # os.environ["LOGURU_LEVEL"] = "TRACE"
    os.environ["LOGURU_LEVEL"] = "ERROR"
    os.environ['LOGGER_LEVEL'] = 'Error'
    os.environ["HOME"] = "/home/tt-buda/results/smoke_test"
    os.environ["PYBUDA_DISABLE_REPORTIFY_DUMP"] = "0"
    test_module_direct_pytorch()
