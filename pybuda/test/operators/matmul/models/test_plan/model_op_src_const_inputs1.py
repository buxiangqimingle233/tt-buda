# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
#
#   Matmul operator defined by PyBuda API
#   These kinds of tests test only single specific operator through different PyBuda architectures
# 


import torch

import pybuda

from pybuda import PyBudaModule


class BudaMatmulTest(PyBudaModule):
    """
        Operator Matmul test _ Const Inputs _ const eval pass"

        According to Test plan with this model we are testing:
            1. Op type: Matmul
            2. Operand source: Const Inputs: (const eval pass)
            3. Operand shapes: All cases in combination with this operand source
            4. Operand / output size of dimensions: All cases in combination with this operand source
            5. /
            6. /
        
    """

    def __init__(self, shape1, shape2):
        super().__init__("Operator Matmul test _ Const Inputs _ const eval pass")
        self.testname = "Operator Matmul test _ Const Inputs _ const eval pass"

        self.add_constant("c1")
        self.set_constant("c1", pybuda.Tensor.create_from_torch(torch.rand(*shape1, requires_grad=False), constant=True))

        self.add_constant("c2")
        self.set_constant("c2", pybuda.Tensor.create_from_torch(torch.rand(*shape2, requires_grad=False), constant=True))
        

    def forward(self, x1, x2):

        mm1 = pybuda.op.Matmul("mm1", self.get_constant("c1"),  self.get_constant("c2"))   
        mm2 = pybuda.op.Matmul("mm2", x1, x2)   
        add1 = pybuda.op.Add("add1", mm1, mm2)

        return add1

    def values(self):
        return [item.value() for item in self.inputs]
