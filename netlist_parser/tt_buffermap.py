from tt_graph import Queue

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