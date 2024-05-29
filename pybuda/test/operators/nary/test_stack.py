# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
#
# Tests for testing of stack operator



# GENERAL OP SUPPORT TEST PLAN:
# 1. Operand type - any supported type
# 2. Operand source(s):
# (+)  2.1 From another op
#       - Operator -> input
# (+)  2.2 From tm edge
#       - Combination: operator -> tm -> input
#       - tm -> input
# (+)  2.3 From DRAM queue
#       - input_queue flag = false
#       - Special case of From host? May it be triggered if the operator is not the first node of the network?
#       - Can this be triggered from pybuda.Parameter?
#       - Can this be triggered from big pybuda.Constant?
# (+)  2.4 From DRAM, but prologued (constant)
#       - Constants must be small enough to fit into L1
#       - Verification via netlists that scenario is triggered
#       - Input are not prologued for microbatch size = 1
# (+)  2.5 Const Inputs (const eval pass)
#       - Operator where all inputs are constants. Does it make difference if tensor is big > L1
#       - Verification via netlists that scenario is triggered???
# (+)  2.6 From host
#       - Input tensor as input of network -> Operator is first node in network and input_queue flag = true
#       - Can this scenario be triggered from pybuda.Parameter?
#       - Can this be triggered from big pybuda.Constant?
# 3 Operand shapes type(s):
# (+)  3.1 Full tensor (i.e. full expected shape)
#       - Is 3 dims max for all ops? Ex. Conv is 3d max
# (+)  3.2 Tensor reduce on one or more dims to 1
#       - Vector
#       - Only one dim is not equal to 1
# (/)  3.3 Scalar
#       - Create tensor of dimension equal to 0 (tensor from scalar) or just to use scalar as simple value
# 4. Operand / output size of dimensions (few examples of each, 10 values total)
# (+)  4.1 Divisible by 32
# (+)  4.2 Prime numbers
# (+)  4.3 Very large (thousands, 10s of thousands)
#       - 100x100, 100x1000
#       - maybe nightly only
# (+)  4.4 Extreme ratios between height/width
#      4.5 ...probably many more interesting combinations here
# 5. Data format - all supported formats
# (/)  5.1 Output DF
# (/)  5.2 Intermediate DF
# (/)  5.3 Accumulation DF
# (+)  5.4 Operand DFs
# (+) 6. Math fidelity - LoFi, HiFi2a, Hifi2b, Hifi3, Hifi4
# (/) 7. Special attributes - if applicable.. like approx_mode for Exp, for example

import pytest

import pybuda
import pybuda.op
import pybuda.tensor
import torch

from pybuda import PyBudaModule, VerifyConfig
from pybuda.config import _get_global_compiler_config
from pybuda.verify import TestKind, verify_module
from test.operators.utils import netlist_utils

# Currently, verify_module for the Stack operator and Stack operator by it self
# works only in case of axis = 1. This test demonstrate this case. 
# All tests will fail except in case of axis = 1.
# Error message:
#     "...
#      [Golden-input_shape0--3] - AssertionError: Setting a tensor value of incorrect shape: (2, 1, 3, 3) vs torch.Size([1, 2, 3, 3])
#      [Golden-input_shape0--2] - AssertionError: Setting a tensor value of incorrect shape: (1, 2, 3, 3) vs torch.Size([1, 3, 2, 3])
#      [Golden-input_shape0--1] - AssertionError: Setting a tensor value of incorrect shape: (1, 3, 2, 3) vs torch.Size([1, 3, 3, 2])
#      [Golden-input_shape0-0] - pybuda._C.UnsupportedHWOpsError: Splice op can only operate on dims 1, 2, or 3
#      [Golden-input_shape0-2] - RuntimeError: TT_ASSERT @ pybuda/csrc/graph_lib/shape.cpp:114: (i >= 0) && (i < (int)dims_.size())
#      ..."
axises = [-3, -2, -1, 0, 1, 2]
input_shapes = [(1, 3, 3)]
@pytest.mark.skip("Bug: Stack operator doesn't work for axis values different of 1.")
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", input_shapes)
def test_stack_invalid_axis(test_device, axis, input_shape):
       
        class Model(PyBudaModule):
            def __init__(self, name):
                super().__init__(name)
    
            def forward(self, x, y):
                result = pybuda.op.Stack("Stack0", x, y, axis=axis)
                print(f"*** result:\n{result}")
                return result
            
        mod = Model("test_stack_invalid_axis_model")
        input_shapes = tuple([input_shape for _ in range(2)])
        print(f"***input_shapes: {input_shapes}")
    
        verify_module(
            mod,
            input_shapes=input_shapes,
            verify_cfg=VerifyConfig(
                test_kind=TestKind.INFERENCE,
                devtype=test_device.devtype,
                arch=test_device.arch,
            ), 
        )


# Stack operator works in PyTorch and PyBuda well for all axises except
# that PyBuda doesn't work for axis = -2 and axis = -1.
axises = [-3, -2, -1, 0, 1, 2]
@pytest.mark.skip("Stack operator doesn't work for axis values equal to -2 or -1.")
@pytest.mark.parametrize("axis", axises)
def test_stack_torch_and_buda(axis):

    x_torch = torch.tensor([[1, 2, 3],
                            [4, 5, 6],
                            [7, 8, 9]])

    # PyTorch stack operator always pass
    result_torch = torch.stack([x_torch, x_torch], dim=axis)

    x_buda = pybuda.tensor.Tensor.create_from_torch(x_torch, dev_data_format=pybuda.DataFormat.Int8)

    # PyBuda stack operator pass for all axises except -2 and -1
    result_buda = pybuda.op.Stack("Stack0", x_buda, x_buda, axis=axis)

    # If PyBuda operator doesn't fail, results are always the same as in PyTorch
    # Here we are avoiding verify_module because it fails in some cases.
    output_are_the_same = torch.eq(result_torch, pybuda.tensor.Tensor.to_pytorch(result_buda)).all()
    assert output_are_the_same


# 3 Operand shapes type(s):
# Stack operator works only for axis = 1 and input shape = (1, 1, 3)
# 
# Error message:
#     "...
#      [Golden-input_shape0--2] - AssertionError: Setting a tensor value of incorrect shape: (2, 1, 3) vs torch.Size([1, 2, 3])
#      [Golden-input_shape0--1] - AssertionError: Setting a tensor value of incorrect shape: (1, 2, 3) vs torch.Size([1, 3, 2])
#      [Golden-input_shape0-0] - pybuda._C.UnsupportedHWOpsError: Splice op can only operate on dims 1, 2, or 3
#      [Golden-input_shape0-1] - AttributeError: 'pybuda._C.balancer.OpModel' object has no attribute 'get_sparse_metadata'
#      [Golden-input_shape1--2] - AssertionError: Setting a tensor value of incorrect shape: (1, 2, 1, 3) vs torch.Size([1, 1, 2, 3])
#      [Golden-input_shape1--1] - AssertionError: Setting a tensor value of incorrect shape: (1, 1, 2, 3) vs torch.Size([1, 1, 3, 2])
#      [Golden-input_shape1-0] - pybuda._C.UnsupportedHWOpsError: Splice op can only operate on dims 1, 2, or 3
#      [Golden-input_shape2--2] - AssertionError: Setting a tensor value of incorrect shape: (1, 3, 2, 3, 3) vs torch.Size([1, 3, 3, 2, 3])
#      [Golden-input_shape2--1] - AssertionError: Setting a tensor value of incorrect shape: (1, 3, 3, 2, 3) vs torch.Size([1, 3, 3, 3, 2])
#      [Golden-input_shape2-0] - pybuda._C.UnsupportedHWOpsError: Splice op can only operate on dims 1, 2, or 3
#      [Golden-input_shape2-1] - AssertionError
#      ============================================== 11 failed, 1 passed in 2.40s ===========================================
#      ..." 
axises = [-2 , -1, 0, 1]
input_shapes = [(1, 3),       # vector, always fails
                (1, 1, 3),    # should be reduced to vector, unexpectedly works
                (1, 3, 3, 3)] # 3-dimensional tensor, always fails
@pytest.mark.skip("Stack operator doesn't work when the input is not 2-dimensional tensor.")
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", input_shapes)
def test_stack_invalid_shape(test_device, axis, input_shape):
        class Model(PyBudaModule):
            def __init__(self, name):
                super().__init__(name)
    
            def forward(self, x, y):
                return pybuda.op.Stack("Stack0", x, y, axis=axis)
            
        mod = Model("test_stack_invalid_shape_model")
        input_shapes = tuple([input_shape for _ in range(2)])
    
        verify_module(
            mod,
            input_shapes=input_shapes,
            verify_cfg=VerifyConfig(
                test_kind=TestKind.INFERENCE,
                devtype=test_device.devtype,
                arch=test_device.arch,
            ), 
        )


# Currently, Stack operator works only for values of axis = 1.
# Also, Stack operator only works for two dimensional matrix.
axises = [1]

def get_input_shapes(microbatch_size=1):
                                              # Here we cover interesting combinations of input shapes:
    return [(microbatch_size, 3, 3),         # 3.1 Full tensor (i.e. full expected shape)
            (microbatch_size, 10, 5),        # 3.1 Full tensor (i.e. full expected shape)
            (microbatch_size, 1, 15),        # 3.2 Tensor reduce on one or more dims to 1
            (microbatch_size, 50, 1),        # 3.2 Tensor reduce on one or more dims to 1
            (microbatch_size, 100, 100),     # 4.3 Very large (thousands, 10s of thousands)
            (microbatch_size, 100, 1000),    # 4.3 Very large (thousands, 10s of thousands)
            (microbatch_size, 1, 10000),     # 4.4 Extreme ratios between height/width
            (microbatch_size, 10000, 1),     # 4.4 Extreme ratios between height/width
            (microbatch_size, 32, 32),       # 4.1 Divisible by 32
            (microbatch_size, 96, 96),       # 4.1 Divisible by 32
            (microbatch_size, 13, 97),       # 4.2 Prime numbers
            ]

#   2.1 From another op
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", get_input_shapes(microbatch_size=1))
def test_stack_inputs_from_another_operand(test_device, axis, input_shape, input_params=[], math_fidelity=None):

    class Model(PyBudaModule):
        def __init__(self, name):
            super().__init__(name)

        def forward(self, x, y):
            # we use Add and Subtract operators to create two operands which are inputs for the Stack operator
            xx = pybuda.op.Add("Add0", x, y)
            yy = pybuda.op.Subtract("Subtract0", x, y)
            output = pybuda.op.Stack("Stack0", xx, yy, axis=axis)
            return output
        
    mod = Model("test_stack_inputs_from_another_operand_model")
    input_shapes = tuple([input_shape for _ in range(2)])

    if(math_fidelity is not None):
        compiler_cfg = _get_global_compiler_config()
        compiler_cfg.default_math_fidelity = math_fidelity

    verify_module(
        mod,
        input_shapes=input_shapes,
        verify_cfg=VerifyConfig(
            test_kind=TestKind.INFERENCE,
            devtype=test_device.devtype,
            arch=test_device.arch,
        ),
        input_params=[input_params],
    )


#   2.2 From tm edge
#    - Combination: operator -> tm -> input
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", get_input_shapes(microbatch_size=1))
def test_stack_inputs_from_tm_edge1(test_device, axis, input_shape, input_params=[], math_fidelity=None):

    class Model(PyBudaModule):
        def __init__(self, name):
            super().__init__(name)

        def forward(self, x, y):
            v1 = pybuda.op.Add("Stack0", x, y)
            v2 = pybuda.op.tm.Transpose("Transpose0", v1, -1, -2)
            v3 = pybuda.op.Stack("Stack1", v2, v2, axis=axis)
            return v3
        
    mod = Model("test_stack_inputs_from_tm_edge1_model")
    input_shapes = tuple([input_shape for _ in range(2)])

    if(math_fidelity is not None):
        compiler_cfg = _get_global_compiler_config()
        compiler_cfg.default_math_fidelity = math_fidelity

    verify_module(
        mod,
        input_shapes=input_shapes,
        verify_cfg=VerifyConfig(
            test_kind=TestKind.INFERENCE,
            devtype=test_device.devtype,
            arch=test_device.arch,
        ),
        input_params=[input_params],
    )


#   2.2 From tm edge
#    - tm -> input
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", get_input_shapes(microbatch_size=1))
def test_stack_inputs_from_tm_edge2(test_device, axis, input_shape, input_params=[], math_fidelity=None):

    class Model(PyBudaModule):
        def __init__(self, name):
            super().__init__(name)

        def forward(self, x, y):
            v1 = pybuda.op.tm.Transpose("Transpose0", x, -1, -2)
            v2 = pybuda.op.tm.Transpose("Transpose1", y, -1, -2)
            v3 = pybuda.op.Stack("Stack1", v1, v2, axis=axis)
            return v3
        
    mod = Model("test_stack_inputs_from_tm_edge2_model")
    input_shapes = tuple([input_shape for _ in range(2)])

    if(math_fidelity is not None):
        compiler_cfg = _get_global_compiler_config()
        compiler_cfg.default_math_fidelity = math_fidelity

    verify_module(
        mod,
        input_shapes=input_shapes,
        verify_cfg=VerifyConfig(
            test_kind=TestKind.INFERENCE,
            devtype=test_device.devtype,
            arch=test_device.arch,
        ),
        input_params=[input_params],
    )


#   2.3 From DRAM queue
#    - input_queue flag = false
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", get_input_shapes(microbatch_size=1))
def test_stack_inputs_from_dram_queue(test_device, axis, input_shape, input_params=[], math_fidelity=None):

    class Model(PyBudaModule):
        def __init__(self, name):
            super().__init__(name)

        def forward(self, x, y):
            return pybuda.op.Stack("Stack0", x, y, axis=axis)
        
    mod = Model("test_stack_inputs_from_dram_queue_model")
    input_shapes = tuple([input_shape for _ in range(2)])

    compiler_cfg = _get_global_compiler_config()
    compiler_cfg.input_queues_on_host = False
    if(math_fidelity is not None):
        compiler_cfg.default_math_fidelity = math_fidelity

    verify_module(
        mod,
        input_shapes=input_shapes,
        verify_cfg=VerifyConfig(
            test_kind=TestKind.INFERENCE,
            devtype=test_device.devtype,
            arch=test_device.arch,
        ),
        input_params=[input_params],
    )
    file_path = pybuda.pybudaglobal.get_devices()[0]._compile_output.netlist_filename
    assert netlist_utils.read_netlist_value(file_path, "/queues/x/loc") == 'dram'
    assert netlist_utils.read_netlist_value(file_path, "/queues/y/loc") == 'dram'


def get_input_shapes_prologued():
                                              # Here we cover interesting combinations of input shapes:
    return [((2, 3, 3),      True, False),  #0        # 3.1 Full tensor (i.e. full expected shape)
            ((2, 3, 3),      False, True),  #1        # 3.1 Full tensor (i.e. full expected shape)
            ((2, 3, 3),      None, True),   #2        # 3.1 Full tensor (i.e. full expected shape)
            ((1, 3, 3),      True, False),  #3        # 3.1 Full tensor (i.e. full expected shape)
            ((1, 3, 3),      False, True),  #4        # 3.1 Full tensor (i.e. full expected shape)
            ((1, 3, 3),      None, True),   #5 !!!    # 3.1 Full tensor (i.e. full expected shape) - not according to documentation!
            ((2, 10, 5),     None, True),   #6        # 3.1 Full tensor (i.e. full expected shape)
            ((2, 1, 15),     None, True),   #7        # 3.2 Tensor reduce on one or more dims to 1
            ((2, 50, 1),     None, True),   #8        # 3.2 Tensor reduce on one or more dims to 1
            ((2, 100, 100),  None, True),   #9        # 4.3 Very large (thousands, 10s of thousands)
            ((2, 100, 1000), None, False),  #10       # 4.3 Very large (thousands, 10s of thousands)
            ((2, 1, 10000),  None, False),  #11       # 4.4 Extreme ratios between height/width
            ((2, 10000, 1),  None, False),  #12       # 4.4 Extreme ratios between height/width
            ((2, 32, 32),    None, True),   #13       # 4.1 Divisible by 32
            ((2, 96, 96),    None, True),   #14       # 4.1 Divisible by 32
            ((2, 13, 97),    None, True),   #15       # 4.2 Prime numbers
            ]


#   2.4 From DRAM, but prologued (constant)
#    - Constants must be small enough to fit into L1
#    - Input are not prologued for microbatch size = 1
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape, default_dram_params, should_prolog", get_input_shapes_prologued())
def test_stack_inputs_from_dram_prologued(test_device, axis, input_shape, default_dram_params, should_prolog, input_params=[], math_fidelity=None):
    
    class Model(PyBudaModule):
        def __init__(self, name):
            super().__init__(name)

            def my_rand(*shape, requires_grad=False):
                return (torch.rand(*shape, requires_grad=requires_grad) - 0.5).detach()

            t = input_shape[1:]
            self.shape_input = (1, *t)

            self.add_constant("c")
            self.set_constant("c", pybuda.Tensor.create_from_torch(my_rand(*self.shape_input), constant=True))


        def forward(self, x):
            return pybuda.op.Stack("Stack0", self.get_constant("c"), x, axis=axis)
        
    mod = Model("test_stack_inputs_from_dram_prologued_model")

    compiler_cfg = _get_global_compiler_config()
    compiler_cfg.default_dram_parameters = default_dram_params
    compiler_cfg.input_queues_on_host = False
    if(math_fidelity is not None):
        compiler_cfg.default_math_fidelity = math_fidelity

    verify_module(
        mod,
        input_shapes=[input_shape],
        verify_cfg=VerifyConfig(
            test_kind=TestKind.INFERENCE,
            devtype=test_device.devtype,
            arch=test_device.arch,
        ),
        input_params=[input_params],
    )
    file_path = pybuda.pybudaglobal.get_devices()[0]._compile_output.netlist_filename
    d = netlist_utils.read_netlist_value(file_path, "/programs/0/run_fwd_0/4/execute/queue_settings/input_0_Stack0")
    if should_prolog:
        assert d['prologue']
    else:
        assert not d['prologue']


#   2.5 Const Inputs (const eval pass)
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", get_input_shapes(microbatch_size=1))
def test_stack_inputs_from_constants(test_device, axis, input_shape, input_params=[], math_fidelity=None):
     
    class Model(PyBudaModule):
        def __init__(self, name):
            super().__init__(name)

            def my_rand(*shape, requires_grad=False):
                return (torch.rand(*shape, requires_grad=requires_grad) - 0.5).detach()

            self.shape_input = input_shape

            self.add_constant("c1")
            self.set_constant("c1", pybuda.Tensor.create_from_torch(my_rand(*self.shape_input), constant=True))

            self.add_constant("c2")
            self.set_constant("c2", pybuda.Tensor.create_from_torch(my_rand(*self.shape_input), constant=True))
       
            self.inputs = [
                pybuda.Tensor.create_from_torch(my_rand(*self.shape_input))
            ]

        def forward(self, x, y):
            v1 = pybuda.op.Stack("Stack0", self.get_constant("c1"), self.get_constant("c2"), axis=axis)
            # v2 and v3 consume inputs
            v2 = pybuda.op.Add("Add0", x, y)
            v3 = pybuda.op.Add("Add1", v1, v2)
            return v3

    mod = Model("test_stack_inputs_from_constants_model")
    input_shapes = tuple([input_shape for _ in range(2)])

    if(math_fidelity is not None):
        compiler_cfg = _get_global_compiler_config()
        compiler_cfg.default_math_fidelity = math_fidelity

    verify_module(
        mod,
        input_shapes=input_shapes,
        verify_cfg=VerifyConfig(
            test_kind=TestKind.INFERENCE,
            devtype=test_device.devtype,
            arch=test_device.arch,
        ),
        input_params=[input_params],
    )
    # Here we check there is no key with "Stack" in the netlist in graphs section
    file_path = pybuda.pybudaglobal.get_devices()[0]._compile_output.netlist_filename
    d = netlist_utils.read_netlist_value(file_path, "/graphs/fwd_0_0_temporal_epoch_0")
    for key in d.keys():
        assert "Stack" not in key


#   2.6 From host - case of two tensors as input
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", get_input_shapes(microbatch_size=1))
def test_stack_inputs_from_host_2(test_device, axis, input_shape, input_params=[], math_fidelity=None):

    class Model(PyBudaModule):
        def __init__(self, name):
            super().__init__(name)

        def forward(self, x, y):
            return pybuda.op.Stack("Stack0", x, y, axis=axis)
        
    mod = Model("test_stack_inputs_from_host_2_model")
    input_shapes = tuple([input_shape for _ in range(2)])

    if(math_fidelity is not None):
        compiler_cfg = _get_global_compiler_config()
        compiler_cfg.default_math_fidelity = math_fidelity

    verify_module(
        mod,
        input_shapes=input_shapes,
        verify_cfg=VerifyConfig(
            test_kind=TestKind.INFERENCE,
            devtype=test_device.devtype,
            arch=test_device.arch,
        ),
        input_params=[input_params],
    )


#   2.6 From host - case of 3, 7, and 15 tensors as input
@pytest.mark.parametrize("axis", axises)
@pytest.mark.parametrize("input_shape", get_input_shapes(microbatch_size=1))
@pytest.mark.parametrize("number_of_operands", [3, 7, 15])
def test_stack_inputs_from_host_multiple_operands(test_device, axis, input_shape, number_of_operands, input_params=[], math_fidelity=None):

    class Model(PyBudaModule):
        def __init__(self, name):
            super().__init__(name)

        def forward(self, *x):
            return pybuda.op.Stack("Stack0", *x, axis=axis)
        
    mod = Model("test_stack_inputs_from_host_multiple_operands")
    input_shapes = tuple([input_shape for _ in range(number_of_operands)])

    if(math_fidelity is not None):
        compiler_cfg = _get_global_compiler_config()
        compiler_cfg.default_math_fidelity = math_fidelity

    verify_module(
        mod,
        input_shapes=input_shapes,
        verify_cfg=VerifyConfig(
            test_kind=TestKind.INFERENCE,
            devtype=test_device.devtype,
            arch=test_device.arch,
        ),
        input_params=[input_params],
    )


# Operand Data Format and Math Fidelity

# First, we will test only by fixing one axis and one input shape.
axis = 1
def get_single_shape(microbatch_size=1):
    return (microbatch_size, 3, 3)        # Full tensor, small size

# We will not test all combinations of Data Format and Math Fidelity
# because it would be too much tests. 
#   1. First we will choose Data Format to be Float16_b and test all Math Fidelity values
#   2. Then we will set Math Fidelity to HiFi4 and test all Data Formats. 

### 1. ####################################################################################

#   5.4 Operand DFs
verify_input_params=[ 
                        {"dev_data_format": pybuda.DataFormat.Float16_b},
                    ]

#  6. Math fidelity - LoFi, HiFi2a, Hifi2b, Hifi3, Hifi4
compiler_math_fidelity = [
                            pybuda.MathFidelity.LoFi,
                            pybuda.MathFidelity.HiFi2,
                            pybuda.MathFidelity.HiFi3,
                            pybuda.MathFidelity.HiFi4,
                         ]


# Unfortunatelly, we can't call all test functions in just one test, because
# reset of the compiler configuration and device state is not possible.

@pytest.mark.parametrize("math_fidelity", compiler_math_fidelity)
def test_stack_mf_inputs_from_another_operand(test_device, math_fidelity):
    test_stack_inputs_from_another_operand(test_device, axis, get_single_shape(), verify_input_params, math_fidelity)


# @pytest.mark.parametrize("math_fidelity", compiler_math_fidelity)
# def test_stack_mf_from_tm_edge1(test_device, math_fidelity):
#     test_stack_inputs_from_tm_edge1(test_device, axis, get_single_shape(), verify_input_params, math_fidelity)


# @pytest.mark.parametrize("math_fidelity", compiler_math_fidelity)
# def test_stack_mf_from_tm_edge2(test_device, math_fidelity):
#     test_stack_inputs_from_tm_edge2(test_device, axis, get_single_shape(), verify_input_params, math_fidelity)


# @pytest.mark.parametrize("math_fidelity", compiler_math_fidelity)
# def test_stack_mf_from_dram_queue(test_device, math_fidelity):
#     test_stack_inputs_from_dram_queue(test_device, axis, get_single_shape(), verify_input_params, math_fidelity)


# @pytest.mark.parametrize("math_fidelity", compiler_math_fidelity)
# def test_stack_mf_from_dram_prologued(test_device, math_fidelity):
#     test_stack_inputs_from_dram_prologued(test_device, axis, get_single_shape(microbatch_size=2), verify_input_params, math_fidelity)


# @pytest.mark.parametrize("math_fidelity", compiler_math_fidelity)
# def test_stack_mf_from_constants(test_device, math_fidelity):
#     test_stack_inputs_from_constants(test_device, axis, get_single_shape(), verify_input_params, math_fidelity)


# @pytest.mark.parametrize("math_fidelity", compiler_math_fidelity)
# def test_stack_mf_from_host_2(test_device, math_fidelity):
#     test_stack_inputs_from_host_2(test_device, axis, get_single_shape(), verify_input_params, math_fidelity)


# @pytest.mark.parametrize("math_fidelity", compiler_math_fidelity)
# def test_stack_mf_from_host_multiple_operands(test_device, math_fidelity):
#     test_stack_inputs_from_host_multiple_operands(test_device, axis, get_single_shape(), 3, verify_input_params, math_fidelity)


### 2. ####################################################################################

#   5.4 Operand DFs
verify_input_params=[
                        {"dev_data_format": pybuda.DataFormat.Bfp2},
                        {"dev_data_format": pybuda.DataFormat.Bfp2_b},
                        {"dev_data_format": pybuda.DataFormat.Bfp4},
                        {"dev_data_format": pybuda.DataFormat.Bfp4_b},
                        {"dev_data_format": pybuda.DataFormat.Bfp8},
                        {"dev_data_format": pybuda.DataFormat.Bfp8_b},
                        {"dev_data_format": pybuda.DataFormat.Float16},  
                        {"dev_data_format": pybuda.DataFormat.Float16_b},
                        {"dev_data_format": pybuda.DataFormat.Float32},
                        {"dev_data_format": pybuda.DataFormat.Int8},
                        {"dev_data_format": pybuda.DataFormat.Lf8},
                        {"dev_data_format": pybuda.DataFormat.RawUInt16},
                        {"dev_data_format": pybuda.DataFormat.RawUInt32},
                        {"dev_data_format": pybuda.DataFormat.RawUInt8},
                        {"dev_data_format": pybuda.DataFormat.UInt16},
                    ]

#  6. Math fidelity
compiler_math_fidelity = pybuda.MathFidelity.HiFi4


@pytest.mark.parametrize("input_params", verify_input_params)
def test_stack_df_inputs_from_another_operand(test_device, input_params):
    test_stack_inputs_from_another_operand(test_device, axis, get_single_shape(), input_params, compiler_math_fidelity)


# @pytest.mark.parametrize("input_params", verify_input_params)
# def test_stack_df_from_tm_edge1(test_device, input_params):
#     test_stack_inputs_from_tm_edge1(test_device, axis, get_single_shape(), input_params, compiler_math_fidelity)


# @pytest.mark.parametrize("input_params", verify_input_params)
# def test_stack_df_from_tm_edge2(test_device, input_params):
#     test_stack_inputs_from_tm_edge2(test_device, axis, get_single_shape(), input_params, compiler_math_fidelity)


# @pytest.mark.parametrize("input_params", verify_input_params)
# def test_stack_df_from_dram_queue(test_device, input_params):
#     test_stack_inputs_from_dram_queue(test_device, axis, get_single_shape(), input_params, compiler_math_fidelity)


# @pytest.mark.parametrize("input_params", verify_input_params)
# def test_stack_df_from_dram_prologued(test_device, input_params):
#     test_stack_inputs_from_dram_prologued(test_device, axis, get_single_shape(microbatch_size=2), input_params, compiler_math_fidelity)


# @pytest.mark.parametrize("input_params", verify_input_params)
# def test_stack_df_from_constants(test_device, input_params):
#     test_stack_inputs_from_constants(test_device, axis, get_single_shape(), input_params, compiler_math_fidelity)


# @pytest.mark.parametrize("input_params", verify_input_params)
# def test_stack_df_from_host_2(test_device, input_params):
#     test_stack_inputs_from_host_2(test_device, axis, get_single_shape(), input_params, compiler_math_fidelity)


# @pytest.mark.parametrize("input_params", verify_input_params)
# def test_stack_df_from_host_multiple_operands(test_device, input_params):
#     test_stack_inputs_from_host_multiple_operands(test_device, axis, get_single_shape(), 3, input_params, compiler_math_fidelity)
