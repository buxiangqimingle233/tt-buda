# SPDX-FileCopyrightText: © 2024 Tenstorrent AI ULC

# SPDX-License-Identifier: Apache-2.0
import os
from tt_object import TTObjectIDDict
import tt_util as util
from tt_graph import Graph, Queue
from tt_temporal_epoch import TemporalEpoch
from tt_grayskull import GrayskullDevice
from tt_device import Device
from copy import copy
from collections import defaultdict


class QueueBufferMapQueue:
    def __init__(self, queue: Queue, grid_r, grid_c):
        self.queue = queue
        self.grid_r = None
        self.grid_c = None
        self.producer_buffer_id = None
        self.consumer_buffers = set()

    def id(self):
        return (self._queue.id(), self.grid_r, self.grid_c)

    def __hash__(self):
        return self.id()

    def set_producer_buffer(self, buffer_id):
        # TODO: assert self.producer_buffer_id is None
        self.producer_buffer_id = buffer_id

    def has_op_producer(self):
        return self.producer_buffer_id is not None

    def add_consumer_buffer(self, buffer_id):
        self.consumer_buffers.add(buffer_id)


class QueueBufferMap:
    def __init__(self):
        self.location_queue_map: Dict[QueueBufferMapQueue] = dict()
        self.queue_names = dict()
        self.queue_producer_map = dict()
        pass

    def get_queue_producer_buffer(self, queue_name, grid_r, grid_c):
        # Returns a tuple (temporal epoch id, buffer id)
        return self.queue_producer_map[queue_name][grid_r][grid_c]

    def get_queue_name(self, chip_id, dram_channel, dram_addr, temporal_epoch):
        return self.queue_names[(chip_id, dram_channel, dram_addr, temporal_epoch)]

    def get_queue_buffer(
        self, chip_id: int, dram_channel: int, dram_addr: int, temporal_epoch: int
    ):
        return self.location_queue_map[
            (chip_id, dram_channel, dram_addr, temporal_epoch)
        ]

    def add_queue_buffer(
        self,
        chip_id: int,
        dram_channel: int,
        dram_addr: int,
        temporal_epoch: int,
        queue: QueueBufferMapQueue,
    ):
        self.location_queue_map[(chip_id, dram_channel, dram_addr, temporal_epoch)] = (
            queue
        )

    def set_queue_producer_buffer(
        self, queue: QueueBufferMapQueue, producer_buffer_id: int
    ):
        self.location_queue_map[
            (chip_id, dram_channel, dram_addr, temporal_epoch)
        ].set_producer_buffer(producer_buffer_id)

    def add_queue_output_buffer(
        self,
        chip_id: int,
        dram_channel: int,
        dram_addr: int,
        temporal_epoch: int,
        buffer_id: int,
    ):
        self.location_queue_map[
            (chip_id, dram_channel, dram_addr, temporal_epoch)
        ].add_consumer_buffer(buffer_id)


# HACK: No runtime data yaml file needed, hardcoded with inputs instead
class Simplified_Netlist:
    def __init__(self, netlist_filepath, rundir):
        # 1. Set the file. It will be lazy loaded on first access
        assert netlist_filepath is not None
        
        self.rundir = rundir
        self.netlist_file = util.YamlFile(netlist_filepath)

        # initialize the queue buffer map
        self._epoch_id_to_graph_names_map = dict()
        self._graph_name_to_epoch_id_map = dict()
        self._epoch_ids = util.set()
        self.build_epoch_id_map()

        # 2. Load the netlist 
        self._name_consumers_map = defaultdict(list)
        self._op_epoch_map = dict()
        self._addr_queue_map = dict()
        self.load_netlist_data()

        self.temporal_epochs = TTObjectIDDict()
        self.graphs = TTObjectIDDict()
        
        # This is invoked by tt_stream
        # self.devices = self.netlist_file.root["devices"]
        self.devices = [GrayskullDevice(0, "grayskull", {}, "/home/tt-buda/third_party/budabackend/device/grayskull_10x12.yaml", None)]

        # 3. Load pipegen/blob yamls
        self.load_temporal_epochs(rundir)

        # 4. Cache the output_ops for each queue
        all_queue_ids = self._queues.keys()
        for graph_id, graph in self.graphs.items():
            for op_id, op in graph.ops.items():
                for input in op.root["inputs"]:
                    if input in all_queue_ids:
                        self._queues[input].output_ops.add(op)

        for _, graph in self.graphs.items():
            graph.device = self.devices[graph.device_id()]


    def build_epoch_id_map(self):
        '''
        Build the mapping between epoch id and graph name
            self._epoch_id_to_graph_names_map: eid --> graph_name
            self._graph_name_to_epoch_id_map: graph_name --> eid
        '''

        # FIXME: We now assume a the bijection mapping between epoch id and graph name
        # It's important to notice that an epoch could map to multiple graphs simultaneously in Wormhole
        # Check the URL: https://github.com/tenstorrent/tt-budabackend/blob/58fab9cd7ac53176363fc3ee61d40f434778c964/docs/public/netlist.md
        global_epoch_id = 0
        for graph_name in self.graph_names():
            # epoch_id = self.graph_name_to_epoch_id(graph_name)
            epoch_id = global_epoch_id      # FIXME: the epoch id is stored in runtime.yaml file, fix it ASAP we got the runtime file
                                            # Or we could traverse the rundir to get the epoch id and get the graph

            self._epoch_ids.add(epoch_id)
            self._graph_name_to_epoch_id_map[graph_name] = epoch_id
            if epoch_id not in self._epoch_id_to_graph_names_map:
                self._epoch_id_to_graph_names_map[epoch_id] = util.set()
            self._epoch_id_to_graph_names_map[epoch_id].add(graph_name)
            
            global_epoch_id += 1


    def load_netlist_data(self):
        self._queues = TTObjectIDDict()
        for queue_name in self.queue_names():
            queue = Queue(queue_name, self.netlist_file.root["queues"][queue_name])
            self._queues[queue.id()] = queue
            q_yaml = self.netlist_file.root["queues"][queue_name]
            self._name_consumers_map[q_yaml["input"]].append(queue_name)

            if q_yaml["loc"] == "dram":
                target_device = q_yaml["target_device"]
                grid_size_r, grid_size_c = q_yaml["grid_size"]
                grid_r, grid_c = 0, 0
                for dram_channel, dram_addr in q_yaml["dram"]:
                    self._addr_queue_map[(target_device, dram_channel, dram_addr)] = (
                        QueueBufferMapQueue(queue, grid_r, grid_c)
                    )
                    grid_c += 1
                    assert grid_r < grid_size_r
                    if grid_c == grid_size_c:
                        grid_c = 0
                        grid_r += 1


    def load_temporal_epochs(self, rundir):

        # Create graphs 
        for graph_name in self.graph_names():
            # Create the graph
            g = Graph(self, graph_name, self.netlist_file.root["graphs"][graph_name], rundir)
            self.graphs.add(g)

        # Iterate over all temporal epochs to create a TemporalEpoch object for each epoch and link with graphs
        for epoch_id, graph_sets in self._epoch_id_to_graph_names_map.items():
            graph_list = list(graph_sets)
            graph_dir = f"{rundir}/temporal_epoch_{epoch_id}"
            if not os.path.isdir(graph_dir):
                util.FATAL(f"Error: cannot find directory {graph_dir}")

            pipegen_file = f"{graph_dir}/overlay/pipegen.yaml"
            blob_file = f"{graph_dir}/overlay/blob.yaml"
            te = TemporalEpoch(
                epoch_id,
                self,
                pipegen_file,
                blob_file,
                [self.graph(g_name).root for g_name in graph_list],
            )
            te.graphs = TTObjectIDDict()

            # te.load_blob()
            # te.load_pipegen()

            for g_name in graph_list:
                g = self.graph(g_name)
                te.graphs.add(g)
                g.temporal_epoch = te
            self.temporal_epochs.add(te)

            for op_name, op in te.ops.items():
                self._op_epoch_map[op_name] = te.id()
                for input_name in op.root["inputs"]:
                    self._name_consumers_map[input_name].append(op.id())
        
        print(self.temporal_epochs.first)

    # Returns names of graphs directly from the netlist yaml file
    def graph_names(self):
        return self.netlist_file.root["graphs"].keys()

    # Returns names of queues directly from the netlist yaml file
    def queue_names(self):
        return self.netlist_file.root["queues"].keys()

    def epoch_id_to_graph_names(self, epoch_id):
        return (
            self._epoch_id_to_graph_names_map[epoch_id]
            if epoch_id in self._epoch_id_to_graph_names_map
            else None
        )

    def graph(self, graph_name):
        return self.graphs[graph_name]

    def device_graph_names(self):
        return self._map_graph_names

    def devices(self):
        return self.netlist_file.root["devices"]

    def queue(self, queue_name):
        return self._queues[queue_name]

    def queues(self):
        return self._queues

    # Determines the architecture
    def get_arch(self):
        if "arch_name" in self.runtime_data_yaml.root:
            return self.runtime_data_yaml.root["arch_name"]
        return None

    # Returns all device ids used by the graphs and the queues in the netlist
    def get_device_ids(self):
        device_ids = util.set(
            q["target_device"] for _, q in self.netlist_file.root["queues"].items()
        )
        device_ids.update(
            util.set(
                g["target_device"] for _, g in self.netlist_file.root["graphs"].items()
            )
        )
        return device_ids

    # Renderer
    def __str__(self):
        return f"{type(self).__name__}: {self.netlist_file.filepath}. Graphs({len(self.graph_names())}): {' '.join (self.graph_names())}"

    def __repr__(self):
        return self.__str__()

if __name__ == "__main__":
    a = Simplified_Netlist("/home/tt-buda/direct_pt_netlist.yaml", "/home/tt-buda/net2pipe_output")
    # print(a.temporal_epochs.first().buffers)
    print(a.temporal_epochs.first().streams)
