import struct

class NTHeader:
    def __init__(self, nt_magic, version, benchmark_name, num_nodes, num_cycles, num_packets, notes_length, num_regions, notes, regions):
        self.nt_magic = nt_magic
        self.version = version
        self.benchmark_name = benchmark_name
        self.num_nodes = num_nodes
        self.num_cycles = num_cycles
        self.num_packets = num_packets
        self.notes_length = notes_length
        self.num_regions = num_regions
        self.notes = notes
        self.regions = regions


class NTPacket:
    def __init__(self, cycle, id, addr, type, src, dst, node_types, num_deps, deps):
        self.cycle = cycle
        self.id = id
        self.addr = addr
        self.type = type
        self.src = src
        self.dst = dst
        self.node_types = node_types
        self.num_deps = num_deps
        self.deps = deps


def nt_dump_header(header, fp):
    if header is not None:
        header_pack = struct.pack('If30sBQQLL', header.nt_magic, header.version, header.benchmark_name.encode(), header.num_nodes, header.num_cycles, header.num_packets, header.notes_length, header.num_regions)
        fp.write(header_pack)
        fp.write(header.notes.encode())
        for region in header.regions:
            fp.write(struct.pack('QQQ', region.seek_offset, region.num_cycles, region.num_packets))
    else:
        raise ValueError("dumping NULL header")


def nt_dump_packet(packet, fp):
    if packet is not None:
        packet_pack = struct.pack('QII4B', packet.cycle, packet.id, packet.addr, packet.type, packet.src, packet.dst, packet.node_types, packet.num_deps)
        fp.write(packet_pack)
        for dep in packet.deps:
            fp.write(struct.pack('I', dep))
    else:
        raise ValueError("dumping NULL packet")
