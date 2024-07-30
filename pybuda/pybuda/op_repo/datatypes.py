# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
# Operator repository models


from random import Random
from typing import List, Dict, Tuple, Optional, Callable, Type, Union
from dataclasses import dataclass, field


# Defining a type for tensor shape
TensorShape = Tuple[int, ...]


@dataclass
class OperatorParamNumber:
    name: str
    type: Type[Union[int, float]]
    min_value: Optional[int]
    max_value: Optional[int]


OperatorParam = Union[OperatorParamNumber]


@dataclass
class OperatorDefinition:
    name: str
    full_name: str
    input_num: int
    instantiate: bool = False  # nn in Torch require instantiation in constructor
    constructor_params: List[OperatorParam] = field(default_factory=list)
    forward_code: Optional[Callable[[], str]] = None
    forward_params: List[OperatorParam] = field(default_factory=list)
    operands: List[str] = field(default_factory=list)  # TODO describe operand and shapes
    calc_input_shapes: Optional[Callable[["ShapeCalculationContext", Random], List[TensorShape]]] = None  # calculate input shapes from output shape

    @property
    def is_operator(self) -> bool:
        return not self.instantiate

    @property
    def is_layer(self) -> bool:
        return self.instantiate


class ShapeCalculationContext:

    @property
    def operator(self) -> OperatorDefinition:
        raise NotImplementedError("Operator is not defined")

    @property
    def constructor_kwargs(self) -> Dict[str, object]:
        raise NotImplementedError("constructor_kwargs is not defined")

    @property
    def forward_kwargs(self) -> Dict[str, object]:
        raise NotImplementedError("forward_kwargs is not defined")

    @property
    def output_shape(self) -> TensorShape:
        raise NotImplementedError("output_shape is not defined")

    @property
    def rng_shape(self) -> Random:
        raise NotImplementedError("rng_shape is not defined")


class OperatorRepository:

    def __init__(self, operators: List[OperatorDefinition]):
        self.operators = operators

    def get_by_name(self, name: str):
        return [op for op in self.operators if op.name == name][0]
