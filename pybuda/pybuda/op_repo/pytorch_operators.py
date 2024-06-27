# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
# PyTorch repostiory operators


from .datatypes import OperatorDefinition, OperatorRepository
from .datatypes import OperatorParamNumber
from .shapes import same_input_shapes
from .shapes import linear_inputs
from .shapes import conv2d_inputs
from .shapes import matmul_inputs


# TODO describe operand and shapes
_OPERATORS = [
    OperatorDefinition("linear", "torch.nn.Linear", 1, instantiate=True, constructor_params=[
        OperatorParamNumber("in_features", int, 10, 50),
        OperatorParamNumber("out_features", int, 10, 50),
    ], calc_input_shapes=linear_inputs),
    OperatorDefinition("conv2d", "torch.nn.Conv2d", 1, instantiate=True, constructor_params=[
        OperatorParamNumber("in_channels", int, 10, 50),
        OperatorParamNumber("out_channels", int, 10, 50),
        OperatorParamNumber("kernel_size", int, 3, 3),
        OperatorParamNumber("stride", int, 1, 1),
        OperatorParamNumber("padding", int, 1, 1),
    ], calc_input_shapes=conv2d_inputs),
    OperatorDefinition("relu", "torch.relu", 1, calc_input_shapes=same_input_shapes),
    OperatorDefinition("sqrt", "torch.sqrt", 1, calc_input_shapes=same_input_shapes),
    OperatorDefinition("tanh", "torch.tanh", 1, calc_input_shapes=same_input_shapes),
    # OperatorDefinition("add", "torch.add", 1),
    OperatorDefinition("add", "torch.add", 2, calc_input_shapes=same_input_shapes),

    # Non-linear activation functions
    # HARDTANH = OperatorDefinition("hardtanh", 1)
    # HARDWISH = OperatorDefinition("hardwish", 1)
    # RELU6 = OperatorDefinition("relu6", 1)
    # ELU = OperatorDefinition("elu", 1)
    # SELU = OperatorDefinition("selu", 1)
    # CELU = OperatorDefinition("celu", 1)
    # LEACKY_RELU = OperatorDefinition("leaky_relu", 1)
    # PRELU = OperatorDefinition("prelu", 1)
    # RRELU = OperatorDefinition("rrelu", 1)
    # GLU = OperatorDefinition("glu", 1)
    # GELU = OperatorDefinition("gelu", 1)
    # LOGSIGMOID = OperatorDefinition("logsigmoid", 1)
    # HARDSHRINK = OperatorDefinition("hardshrink", 1)
    # TANHSHRINK = OperatorDefinition("tanhshrink", 1)
    # SOFTSIGN = OperatorDefinition("softsign", 1)
    # SOFTPLUS = OperatorDefinition("softplus", 1)
    # SOFTMIN = OperatorDefinition("softmin", 1)
    # SOFTMAX = OperatorDefinition("softmax", 1)
    # SOFTSHRINK = OperatorDefinition("softshrink", 1)
    # GUMBEL_SOFTMAX = OperatorDefinition("gumbel_softmax", 1)
    # LOG_SOFTMAX = OperatorDefinition("log_softmax", 1)
    # TANH = OperatorDefinition("tanh", 1)
    # SIGMOID = OperatorDefinition("sigmoid", 1)
    # HARDSIGMOID = OperatorDefinition("hardsigmoid", 1)
    # SILU = OperatorDefinition("silu", 1)
    # MISH = OperatorDefinition("mish", 1)
    # BATCH_NORM = OperatorDefinition("batch_norm", 1)
    # GROUP_NORM = OperatorDefinition("group_norm", 1)
    # INSTANCE_NORM = OperatorDefinition("instance_norm", 1)
    # LAYER_NORM = OperatorDefinition("layer_norm", 1)
    # LOCAL_RESPONSE_NORM = OperatorDefinition("local_response_norm", 1)
    # NORMALIZE = OperatorDefinition("normalize", 1)

    OperatorDefinition("matmul", "torch.matmul", 2, calc_input_shapes=matmul_inputs),
    OperatorDefinition("eltwise", "torch.add", 2, calc_input_shapes=same_input_shapes),
]


pytorch_operator_repository = OperatorRepository([op for op in _OPERATORS])
