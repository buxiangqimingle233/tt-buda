# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
import os
import pybuda
import torch

from ..common import benchmark_model
from pybuda.config import _get_global_compiler_config
from transformers import AutoModelForImageClassification


@benchmark_model(configs=["224", "160", "96"])
def mobilenet_v2(training: bool, config: str, microbatch: int, devtype: str, arch: str, data_type: str, math_fidelity: str):

    from pybuda._C.backend_api import BackendDevice
    
    compiler_cfg = _get_global_compiler_config()
    compiler_cfg.enable_auto_transposing_placement = True

    if compiler_cfg.balancer_policy == "default":
        compiler_cfg.balancer_policy = "Ribbon"

    if data_type == "Bfp8_b" and pybuda.detect_available_devices()[0] == BackendDevice.Wormhole_B0:
        os.environ["PYBUDA_ENABLE_DRAM_IO_BUFFER_SCALING"] = "1"
        os.environ["PYBUDA_ENABLE_INPUT_BUFFER_SCALING_FOR_NOC_READERS"] = "1"

    os.environ["PYBUDA_ENABLE_HOST_INPUT_NOP_BUFFERING"] = "1"

    # These are about to be enabled by default.
    #
    os.environ["PYBUDA_RIBBON2_CALCULATE_TARGET_CYCLES"] = "1"

    if data_type == "Fp16_b":
        os.environ["PYBUDA_FORCE_CONV_MULTI_OP_FRACTURE"] = "1"

    if data_type == "Bfp8_b":
        pybuda.config.configure_mixed_precision(name_regex="input.*add.*", output_df=pybuda.DataFormat.Float16_b)
        pybuda.config.configure_mixed_precision(op_type="add", output_df=pybuda.DataFormat.Float16_b)
        pybuda.config.configure_mixed_precision(
            op_type="depthwise", 
            input_df={1: (pybuda.DataFormat.Float16_b, False),}, 
            output_df=pybuda.DataFormat.Float16_b, 
            math_fidelity=pybuda.MathFidelity.HiFi2
        )
        pybuda.config.configure_mixed_precision(op_type="multiply", math_fidelity=pybuda.MathFidelity.HiFi2)
        pybuda.config.configure_mixed_precision(op_type="matmul", math_fidelity=pybuda.MathFidelity.HiFi2)

    # Set model parameters based on chosen task and model configuration
    if config == "224":
        model_name = "google/mobilenet_v2_1.0_224"
        img_res = 224
    elif config == "160":
        model_name = "google/mobilenet_v2_0.75_160"
        img_res = 160
    elif config == "96":
        model_name = "google/mobilenet_v2_0.35_96"
        img_res = 96
    else:
        raise RuntimeError("Unknown config")

    # Load model
    model = AutoModelForImageClassification.from_pretrained(model_name)

    # Configure model mode for training or evaluation
    if training:
        model.train()
    else:
        model.eval()

    modules = {"tt": pybuda.PyTorchModule(f"pt_mobilenet_v2_{config}", model)}

    input_shape = (microbatch, 3, img_res, img_res)
    inputs = [torch.rand(*input_shape)]
    targets = tuple()

    # Add loss function, if training
    if training:
        model["cpu-loss"] = pybuda.PyTorchModule("l1loss", torch.nn.L1Loss())
        targets = [torch.rand(1, 100)]

    return modules, inputs, targets, {}
