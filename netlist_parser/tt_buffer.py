# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
from tt_object import TTObject, TTObjectIDDict
from tt_coordinate import OnChipCoordinate


# Constructed from epoch's pipegen.yaml. Contains information about a buffer.
class Buffer(TTObject):
    def __init__(self, graph, data):
        data["core_coordinates"] = tuple(data["core_coordinates"])
        self.root = data
        self._id = self.root["uniqid"]
        self.replicated = False
        self.graph = graph
        self.stream_id = None
        self.input_of_pipes = TTObjectIDDict()
        self.output_of_pipes = TTObjectIDDict()

        self.input_buffer_of_same_op = TTObjectIDDict()
        self.output_buffer_of_same_op = TTObjectIDDict()

        self.replicated_buffers = []

    # Renderer
    def __str__(self):
        r = self.root
        R = r["core_coordinates"][0]
        C = r["core_coordinates"][1]
        return f"{super().__str__()} {r['md_op_name']}:[{R},{C}]"

    def is_output_of_pipe(self):
        return len(self.output_of_pipes) > 0

    def is_input_of_pipe(self):
        return len(self.input_of_pipes) > 0

    def add_replicated_buffer(self, buffer):
        self.replicated_buffers.append(buffer)

    def belongs_to_same_op(self, other_buffer):
        return self.root["md_op_name"] == other_buffer.root["md_op_name"]

    def connect_buffers_of_same_op(self, other_buffers, other_buffer_type="out"):
        if not type(other_buffers) == list:
            other_buffers = [other_buffers]

        # Replicated buffers should also be connected, since they are physically the same buffer but logically assigned to different pipes
        replicated_buffers = [rb for ob in other_buffers for rb in ob.replicated_buffers]
        other_buffers += replicated_buffers
        
        for other_buffer in other_buffers:
            if other_buffer._id == self._id:
                continue
            if other_buffer_type == "out":
                self.output_buffer_of_same_op.add(other_buffer)
                other_buffer.input_buffer_of_same_op.add(self)
            elif other_buffer_type == "in":
                self.input_buffer_of_same_op.add(other_buffer)
                other_buffer.output_buffer_of_same_op.add(self)
            else:
                raise ValueError(f"Invalid buffer type: {other_buffer_type}")

    def is_dram_buffer(self):
        return self.root["core_coordinates"] == (255, 255) or "dram" in self.root["buffer_type"]
    
    def loc(self):
        if self.root["core_coordinates"] == (255, 255): 
            # An (255, 255) coordination indicates an DRAM blob, we should determie its location by dram_channel
            assert "dram" in self.root["buffer_type"]  # dram_io or dram_prelog
            return OnChipCoordinate(*self.graph.device.DRAM_CHANNEL_TO_NOC0_LOC[self.root["dram_chan"]], "noc0", self.graph.device)
        else:
            return OnChipCoordinate(
                *self.root["core_coordinates"], "netlist", self.graph.device
            )
