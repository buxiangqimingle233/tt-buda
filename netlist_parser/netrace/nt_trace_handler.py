import struct
import bz2
import os

NTMAGIC = 0x484A5455

class NTHeader:
    
    def __init__(self, nt_magic=0, version=1.0, benchmark_name='', num_nodes=0, num_cycles=0, num_packets=0, notes_length=0, num_regions=0, notes='', regions=[]):
        self.nt_magic = NTMAGIC
        self.version = 1.0                    # 1.0
        self.benchmark_name = benchmark_name  # Name of the benchmark, 30 char max
        self.num_nodes = num_nodes          # Number of nodes
        self.num_cycles = num_cycles        # Number of simulated cycles, not sure it is used by cnsim, check it 
        self.num_packets = num_packets      # Number of packets
        self.notes_length = notes_length    # Length of notes string
        self.num_regions = num_regions      # Always 1 for now
        self.notes = notes                  # A note string
        self.regions = regions              # (seek_offset, num_cycles, num_pakcets)

    def nt_dump_header(self, fp):
        header = self
        header_pack = struct.pack('If30sBQQII', header.nt_magic, header.version, header.benchmark_name.encode(), header.num_nodes, header.num_cycles, header.num_packets, header.notes_length, header.num_regions)
        fp.write(header_pack)
        fp.write(b'\x00' * 8)                           # 8 char padding
        fp.write(header.notes.encode() + b'\x00')       # null-terminated string, notes_length = len(header.notes.encode) + 1
        assert len(header.regions) == header.num_regions
        for region in header.regions:
            fp.write(struct.pack('QQQ', region[0], region[1], region[2]))

    def nt_read_trheader(self, fp):
        # Read Header
        header_pack = fp.read(struct.calcsize('If30sBQQII'))
        if not header_pack:
            raise ValueError("failed to read trace file header")
        nt_magic, version, benchmark_name, num_nodes, num_cycles, num_packets, notes_length, num_regions = struct.unpack('If30sBQQII', header_pack)
        benchmark_name = benchmark_name.decode().rstrip('\x00')  # remove null-terminating char

        # Error Checking
        if nt_magic != NTMAGIC:
            raise ValueError("invalid trace file: bad magic")
        if version != 1.0:
            raise ValueError(f"trace file is unsupported version: {version}")

        # 8 char padding
        padding = fp.read(8)
        # Read Rest of Header
        notes = None
        if notes_length > 0 and notes_length < 8192:
            notes = fp.read(notes_length)
            if not notes:
                raise ValueError("failed to read trace file header notes")
            try:
                notes = notes.decode().rstrip('\x00')  # remove null-terminating char
            except UnicodeDecodeError:
                notes = notes.decode('utf-8', 'replace').rstrip('\x00')  # replace invalid characters

        regions = None
        if num_regions > 0:
            if num_regions <= 100:
                regions = []
                for _ in range(num_regions):
                    region_pack = fp.read(struct.calcsize('QQQ'))
                    if not region_pack:
                        raise ValueError("failed to read trace file header regions")
                    regions.append(struct.unpack('QQQ', region_pack))
            else:
                raise ValueError("lots of regions... is this correct?")

        # self = NTHeader(nt_magic, version, benchmark_name, num_nodes, num_cycles, num_packets, notes_length, num_regions, notes, regions)
        self.nt_magic, self.version, self.benchmark_name, self.num_nodes, self.num_cycles, self.num_packets, self.notes_length, self.num_regions, self.notes, self.regions \
            = nt_magic, version, benchmark_name, num_nodes, num_cycles, num_packets, notes_length, num_regions, notes, regions
    
    def __str__(self) -> str:
        return f"nt_magic: {self.nt_magic}, version: {self.version}, benchmark_name: {self.benchmark_name}, num_nodes: {self.num_nodes}, num_cycles: {self.num_cycles}, num_packets: {self.num_packets}, notes_length: {self.notes_length}, num_regions: {self.num_regions}, notes: {self.notes}, regions: {self.regions}"


class NTPacket:
    
    def __init__(self, cycle=0, id=0, pkt_size=0, type=0, src=0, dst=0, node_types=0, num_deps=0, deps=[]):
        self.cycle = cycle
        self.id = id
        self.pkt_size = pkt_size        # FIXME: We hack the netrace to integrate packet size to packet.addr field
        self.type = type
        self.src = src
        self.dst = dst
        self.node_types = node_types
        self.num_deps = num_deps
        self.deps = deps

    def nt_dump_packet(self, fp):
        packet = self
        packet_pack = struct.pack('QII5B', packet.cycle, packet.id, packet.pkt_size, packet.type, packet.src, packet.dst, packet.node_types, packet.num_deps)
        fp.write(packet_pack)
        if packet.num_deps > 0:
            for dep in packet.deps:
                fp.write(struct.pack('I', dep))

    def nt_read_packet(self, fp):
        # Read Packet
        packet_pack = fp.read(struct.calcsize('QII5B'))
        if not packet_pack:
            raise ValueError("failed to read packet")
        cycle, id, addr, type, src, dst, node_types, num_deps = struct.unpack('QII5B', packet_pack)

        # Read Dependencies
        deps = None
        if num_deps > 0:
            deps = []
            for _ in range(num_deps):
                dep_pack = fp.read(struct.calcsize('I'))
                if not dep_pack:
                    raise ValueError("failed to read dependencies")
                deps.append(struct.unpack('I', dep_pack)[0])
        self.cycle, self.id, self.pkt_size, self.type, self.src, self.dst, self.node_types, self.num_deps, self.deps \
            = cycle, id, addr, type, src, dst, node_types, num_deps, deps

    def __str__(self):
        return f"cycle: {self.cycle}, id: {self.id}, addr: {self.pkt_size}, type: {self.type}, src: {self.src}, dst: {self.dst}, node_types: {self.node_types}, num_deps: {self.num_deps}, deps: {self.deps}"


class NTTrace:
    def __init__(self, header: NTHeader, packets: list):
        self.header = header
        self.packets = packets

    def __init__(self):
        # FIXME: Check this for debugging
        self.header = NTHeader(nt_magic = NTMAGIC, version=1.0, benchmark_name='tt-netlist', num_nodes=0, \
                            num_cycles=0, num_packets=0, notes_length=0, num_regions=0, notes='', regions=[])
        self.packets = []

    def add_packet(self, packet):
        self.packets.append(packet)
        self.header.num_packets += 1
        self.header.num_cycles = max(self.header.num_cycles, packet.cycle)

    def nt_read(self, filename):
        assert os.path.exists(filename)
        assert filename.endswith('.bz2')
        with bz2.open(filename, 'rb') as fp:
            self.header.nt_read_trheader(fp)

            for _ in range(self.header.num_packets):
                packet = NTPacket()
                packet.nt_read_packet(fp)
                self.packets.append(packet)

    def nt_dump(self, filename):
        with open(filename, 'wb') as fp:
            self.header.nt_dump_header(fp)
            for packet in self.packets:
                packet.nt_dump_packet(fp)
        if os.path.exists(filename + ".bz2"):
            os.remove(filename + ".bz2")
        os.system(f"bzip2 -k {filename}")

    def nt_print_trace(self):
        print(str(self.header))
        print("Packets:")
        for packet in self.packets:
            print(str(packet))


if __name__ == "__main__":
    import bz2
    filename = 'example.tra.bz2'  # replace with your filename

    # Read the compressed file
    trace = NTTrace()
    trace.nt_read(filename)
    trace.nt_print_trace()
    # trace.nt_dump('example.tra2')
