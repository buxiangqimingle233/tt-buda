# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
from typing import Any
from tt_object import TTObject, TTObjectIDDict
from enum import Enum
from typing import List
from netrace.nt_trace_handler import NTPacket

class PipeType(Enum):
    UNICAST = 0
    DEFAULT = 0
    SCATTER = 1
    GATHER = 2
    ALLTOALL = 3

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


    def pipe_to_packets(self) -> List[NTPacket]:
        '''
            This translate the pipe with probably multiple sources and destinations to a list of unicast packets. 
        '''
        ret = []
        packet_ids = self.pipe_to_packet_ids()

        i = 0
        for src in self.src_buffers():
            for dst in self.dst_buffers():
                nt_packet = NTPacket()
                nt_packet.cycle = self.pipe_wait_cycles()
                nt_packet.id = packet_ids[i]
                nt_packet.pkt_size = self.msg_size            # In bytes
                nt_packet.type = self.get_type()
                nt_packet.src = src.loc().to("netrace")
                nt_packet.dst = dst.loc().to("netrace")
                nt_packet.node_types = 0                     
                nt_packet.deps = [item for sublist in [p.pipe_to_packet_ids() for p in self.succeed_pipes()] for item in sublist]
                nt_packet.num_deps = len(nt_packet.deps)
                ret.append(nt_packet)
                i += 1

        return ret
    
    def pipe_to_packet_ids(self) -> List[int]:
        return [i + self._id for i in range(len(self.src_buffers()) * len(self.dst_buffers()))]  

    def pipe_wait_cycles(self):
        return max([i.get_delay_of_attached_op_model() for i in self.input_buffers.values()])

    def get_type(self):
        if (len(self.input_buffers) > 1 and len(self.output_buffers) == 1):
            return PipeType.GATHER
        elif self.input_buffers.first().root["is_scatter"] or (len(self.input_buffers) == 1 and len(self.output_buffers) > 1):
            return PipeType.SCATTER
        elif len(self.input_buffers) > 1 and len(self.output_buffers) > 1:
            return PipeType.ALLTOALL
        else:
            return PipeType.UNICAST

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
    