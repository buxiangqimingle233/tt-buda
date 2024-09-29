# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
from typing import Any
from tt_object import TTObject, TTObjectIDDict


# Constructed from epoch's pipegen.yaml. Contains information about a pipe.
class Pipe(TTObject):
    def __init__(self, graphs, data):
        self.root = data
        self._id = self.root["id"]
        self.graphs = graphs
        self.input_buffers = TTObjectIDDict()
        self.output_buffers = TTObjectIDDict()
        self.stream_id = None

    # Renderer
    def __str__(self):
        return f"{super().__str__()}, inputs: {self.input_buffers}, outputs: {self.output_buffers}"

    def succeed_pipes(self):
        ret = []
        for buffer in self.output_buffers.values():
            # Me, and all my connected buffers, pipe --> input buffer 1 of op1 --> output buffer 1 of op1 --> pipe
            #                                                                 |--> output buffer 2 of op1 --> pipe
            potential_influeced_buffers = list(buffer.output_buffer_of_same_op.values()) + [buffer]
            for b in potential_influeced_buffers:
                for pipe in b.input_of_pipes.values():
                    ret.append(pipe)
        return ret

    def predecessor_pipes(self):
        ret = []
        for buffer in self.input_buffers.values():
            potential_influeced_buffers = list(buffer.input_buffer_of_same_op.values()) + [buffer]
            for b in potential_influeced_buffers:
                for pipe in b.output_of_pipes.values():
                    ret.append(pipe)
        return ret

    def get_msg_size(self):
        # FIXME: We need to handle scatter, gather, direct_connect, forked_connect
        # It seems that the NoC has multicast capabilities
        size = 0
        for ib in self.input_buffers.values():
            size += ib.root['tile_size'] * ib.root['size_tiles']
        return size

    def src_buffers(self):
        return self.input_buffers.values()
    
    def dst_buffers(self):
        return self.output_buffers.values()

    def src_coordinates(self):
        return [b.loc() for b in self.input_buffers.values()]

    def dst_coordinates(self):
        return [b.loc() for b in self.output_buffers.values()]
    