#!/usr/bin/env python3
"""Locate code references to Bedrock storage-item serialization strings.

This is a maintainer diagnostic for validating exact-build signatures. It reads
the server executable directly from an official BDS zip and never executes it.
"""

from __future__ import annotations

import argparse
import bisect
import io
import struct
import zipfile
from pathlib import Path

import capstone
import lief


def section_bytes(section: object) -> bytes:
    return bytes(section.content)


def image_base(binary: object) -> int:
    if isinstance(binary, lief.PE.Binary):
        return int(binary.optional_header.imagebase)
    return 0


def section_address(binary: object, section: object) -> int:
    return image_base(binary) + int(section.virtual_address)


def executable_name(platform: str) -> str:
    return "bedrock_server.exe" if platform == "windows" else "bedrock_server"


def pe_function_ranges(binary: object) -> list[tuple[int, int]]:
    if not isinstance(binary, lief.PE.Binary):
        return []
    pdata = binary.get_section(".pdata")
    if pdata is None:
        return []
    data = section_bytes(pdata)
    base = image_base(binary)
    ranges: list[tuple[int, int]] = []
    for offset in range(0, len(data) - 11, 12):
        begin, end, _unwind = struct.unpack_from("<III", data, offset)
        if begin and end > begin:
            ranges.append((base + begin, base + end))
    ranges.sort()
    return ranges


def containing_range(ranges: list[tuple[int, int]], address: int) -> tuple[int, int] | None:
    if not ranges:
        return None
    index = bisect.bisect_right(ranges, (address, 1 << 64)) - 1
    if index >= 0 and ranges[index][0] <= address < ranges[index][1]:
        return ranges[index]
    return None


def print_disassembly(
    disassembler: object,
    text_data: bytes,
    text_address: int,
    function_range: tuple[int, int],
    highlight: int | None = None,
) -> None:
    function_start, function_end = function_range
    print(
        f"FUNCTION start=0x{function_start:x} end=0x{function_end:x} "
        f"size=0x{function_end - function_start:x}"
    )
    window_start = max(0, function_start - text_address)
    window_end = min(len(text_data), function_end - text_address)
    for instruction in disassembler.disasm(
        text_data[window_start:window_end], text_address + window_start
    ):
        marker = (
            ">"
            if highlight is not None
            and instruction.address <= highlight < instruction.address + instruction.size
            else " "
        )
        print(f"{marker} 0x{instruction.address:x}: {instruction.mnemonic:<9} {instruction.op_str}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", type=Path)
    parser.add_argument("platform", choices=("windows", "linux"))
    parser.add_argument(
        "--needle",
        action="append",
        default=None,
    )
    parser.add_argument("--context", type=int, default=24)
    parser.add_argument("--reference-number", type=int)
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        help="disassemble the PE function containing this VA (or RVA when below image base)",
    )
    parser.add_argument(
        "--find-symbol",
        help="print parsed executable symbols whose names contain this text",
    )
    parser.add_argument(
        "--find-save-context-wrappers",
        action="store_true",
        help="find small PE functions that pass SaveUseCase Clone/Move values to one callee",
    )
    parser.add_argument(
        "--find-lifetime-thunks",
        action="store_true",
        help="find small PE thunks that swap this/argument and pass a member address",
    )
    parser.add_argument(
        "--find-give-lifetimes",
        action="store_true",
        help="find PE functions shaped like tracker lifetime transfer into an owner vector",
    )
    parser.add_argument(
        "--find-callers",
        type=lambda value: int(value, 0),
        help="find direct rel32 call sites targeting this VA (or RVA for PE)",
    )
    args = parser.parse_args()
    needles = args.needle or [
        "storage_item_component_content",
        "dynamic_container_id",
        "minecraft:storage_item",
    ]

    with zipfile.ZipFile(args.zip) as archive:
        raw = archive.read(executable_name(args.platform))
    binary = lief.parse(io.BytesIO(raw))
    if binary is None:
        raise SystemExit("unable to parse server binary")
    function_ranges = pe_function_ranges(binary)

    text = binary.get_section(".text")
    if text is None:
        raise SystemExit("server binary has no .text section")
    text_data = section_bytes(text)
    text_address = section_address(binary, text)

    disassembler = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    disassembler.detail = True
    disassembler.skipdata = True
    if args.find_symbol is not None:
        needle = args.find_symbol.casefold()
        matches = []
        for symbol in binary.symbols:
            name = symbol.name or ""
            if needle in name.casefold():
                matches.append((int(symbol.value), name))
        for address, name in sorted(matches):
            print(f"SYMBOL value=0x{address:x} name={name}")
        if not matches:
            raise SystemExit(f"no parsed symbols contain {args.find_symbol!r}")
        return
    if args.find_callers is not None:
        target = args.find_callers
        base = image_base(binary)
        if base and target < base:
            target += base
        matches: list[tuple[int, str]] = []
        for opcode, mnemonic in ((b"\xe8", "call"), (b"\xe9", "jmp")):
            offset = 0
            while True:
                offset = text_data.find(opcode, offset)
                if offset < 0:
                    break
                if offset + 5 <= len(text_data):
                    displacement = struct.unpack_from("<i", text_data, offset + 1)[0]
                    branch_address = text_address + offset
                    if branch_address + 5 + displacement == target:
                        matches.append((branch_address, mnemonic))
                offset += 1
        for call_address, mnemonic in sorted(matches):
            print(
                f"CALLER {mnemonic}=0x{call_address:x} target=0x{target:x}"
            )
            function_range = containing_range(function_ranges, call_address)
            if function_range is None:
                function_range = (
                    max(text_address, call_address - max(128, args.context * 8)),
                    min(text_address + len(text_data), call_address + max(192, args.context * 12)),
                )
            print_disassembly(
                disassembler,
                text_data,
                text_address,
                function_range,
                highlight=call_address,
            )
        pointer_matches: list[tuple[str, int]] = []
        encoded_target = struct.pack("<Q", target)
        for section in binary.sections:
            data = section_bytes(section)
            offset = 0
            while True:
                offset = data.find(encoded_target, offset)
                if offset < 0:
                    break
                pointer_matches.append(
                    (section.name, section_address(binary, section) + offset)
                )
                offset += 1
        for section_name, address in pointer_matches:
            print(
                f"POINTER section={section_name} address=0x{address:x} "
                f"target=0x{target:x}"
            )
        if not matches and not pointer_matches:
            raise SystemExit(f"no direct rel32 callers target 0x{target:x}")
        return
    if args.address is not None:
        address = args.address
        base = image_base(binary)
        if base and address < base:
            address += base
        function_range = containing_range(function_ranges, address)
        if function_range is None:
            # Stripped ELF builds do not expose PE-style .pdata ranges. The
            # caller may still provide a validated function start; stop at a
            # bounded diagnostic window and let the visible ret delimit it.
            function_range = (address, min(address + max(128, args.context * 8),
                                           text_address + len(text_data)))
        print_disassembly(
            disassembler, text_data, text_address, function_range, highlight=address
        )
        return
    if args.find_save_context_wrappers:
        groups: dict[int, list[tuple[int, int, int]]] = {}
        for function_start, function_end in function_ranges:
            size = function_end - function_start
            if size < 8 or size > 128:
                continue
            start = function_start - text_address
            end = function_end - text_address
            if start < 0 or end > len(text_data):
                continue
            instructions = list(
                disassembler.disasm(text_data[start:end], function_start)
            )
            context_values: set[int] = set()
            direct_calls: list[int] = []
            for instruction in instructions:
                if instruction.mnemonic == "mov" and len(instruction.operands) == 2:
                    destination, source = instruction.operands
                    if (
                        destination.type == capstone.x86.X86_OP_MEM
                        and destination.size == 1
                        and source.type == capstone.x86.X86_OP_IMM
                        and source.imm in (2, 3)
                    ):
                        context_values.add(int(source.imm))
                if instruction.mnemonic in ("call", "jmp") and instruction.operands:
                    target = instruction.operands[0]
                    if target.type == capstone.x86.X86_OP_IMM:
                        direct_calls.append(int(target.imm))
            if len(context_values) == 1 and len(direct_calls) == 1:
                value = next(iter(context_values))
                groups.setdefault(direct_calls[0], []).append(
                    (value, function_start, function_end)
                )
        matches = [
            (target, wrappers)
            for target, wrappers in groups.items()
            if {entry[0] for entry in wrappers} == {2, 3}
        ]
        for target, wrappers in sorted(matches):
            print(f"CALLEE 0x{target:x}")
            for value, start, end in sorted(wrappers):
                print(
                    f"  SaveUseCase={value} wrapper=0x{start:x}-0x{end:x} "
                    f"size=0x{end - start:x}"
                )
        if not matches:
            raise SystemExit("no Clone/Move wrapper pair found")
        return
    if args.find_lifetime_thunks:
        matches: list[tuple[int, int, int, list[object]]] = []
        for function_start, function_end in function_ranges:
            size = function_end - function_start
            if size < 8 or size > 96:
                continue
            start = function_start - text_address
            end = function_end - text_address
            if start < 0 or end > len(text_data):
                continue
            instructions = list(disassembler.disasm(text_data[start:end], function_start))
            member_registers: set[int] = set()
            swapped_this = False
            forwarded_member = False
            targets: list[int] = []
            for instruction in instructions:
                if instruction.mnemonic == "lea" and len(instruction.operands) == 2:
                    destination, source = instruction.operands
                    if (
                        destination.type == capstone.x86.X86_OP_REG
                        and source.type == capstone.x86.X86_OP_MEM
                        and source.mem.base == capstone.x86.X86_REG_RCX
                        and source.mem.disp > 0
                    ):
                        member_registers.add(destination.reg)
                if instruction.mnemonic == "mov" and len(instruction.operands) == 2:
                    destination, source = instruction.operands
                    if (
                        destination.type == capstone.x86.X86_OP_REG
                        and source.type == capstone.x86.X86_OP_REG
                    ):
                        if (
                            destination.reg == capstone.x86.X86_REG_RCX
                            and source.reg == capstone.x86.X86_REG_RDX
                        ):
                            swapped_this = True
                        if (
                            destination.reg == capstone.x86.X86_REG_RDX
                            and source.reg in member_registers
                        ):
                            forwarded_member = True
                if instruction.mnemonic in ("call", "jmp") and instruction.operands:
                    operand = instruction.operands[0]
                    if operand.type == capstone.x86.X86_OP_IMM:
                        targets.append(int(operand.imm))
            if swapped_this and forwarded_member and targets:
                matches.append((function_start, function_end, targets[-1], instructions))
        for start, end, target, instructions in matches:
            print(f"THUNK start=0x{start:x} end=0x{end:x} target=0x{target:x}")
            for instruction in instructions:
                print(f"  0x{instruction.address:x}: {instruction.mnemonic:<8} {instruction.op_str}")
        if not matches:
            raise SystemExit("no lifetime-style PE thunks found")
        return
    if args.find_give_lifetimes:
        if not function_ranges:
            raise SystemExit("lifetime-transfer shape scan currently requires PE .pdata")
        matches: list[tuple[int, int, list[object]]] = []
        for function_start, function_end in function_ranges:
            size = function_end - function_start
            if size < 48 or size > 384:
                continue
            start = function_start - text_address
            end = function_end - text_address
            if start < 0 or end > len(text_data):
                continue
            instructions = list(disassembler.disasm(text_data[start:end], function_start))
            tracker_nodes = False
            owner_vector = False
            has_call = False
            for instruction in instructions:
                for operand in instruction.operands:
                    if operand.type != capstone.x86.X86_OP_MEM:
                        continue
                    memory = operand.mem
                    if (
                        memory.base == capstone.x86.X86_REG_RCX
                        and memory.disp == 0x30
                    ):
                        tracker_nodes = True
                    if (
                        memory.base == capstone.x86.X86_REG_RDX
                        and memory.disp in (0, 8, 0x10)
                    ):
                        owner_vector = True
                if instruction.mnemonic == "call":
                    has_call = True
            if tracker_nodes and owner_vector and has_call:
                matches.append((function_start, function_end, instructions))
        for start, end, instructions in matches:
            print(
                f"GIVE_CANDIDATE start=0x{start:x} end=0x{end:x} "
                f"size=0x{end - start:x}"
            )
            for instruction in instructions:
                print(
                    f"  0x{instruction.address:x}: "
                    f"{instruction.mnemonic:<8} {instruction.op_str}"
                )
        if not matches:
            raise SystemExit("no PE tracker lifetime-transfer candidates found")
        return

    targets: dict[int, str] = {}
    for section in binary.sections:
        data = section_bytes(section)
        base = section_address(binary, section)
        for needle in needles:
            encoded = needle.encode()
            start = 0
            while True:
                offset = data.find(encoded, start)
                if offset < 0:
                    break
                address = base + offset
                targets[address] = needle
                print(f"STRING {needle!r} section={section.name} va=0x{address:x}")
                start = offset + 1

    if not targets:
        raise SystemExit("none of the requested strings were found")

    # MSVC and libc++ commonly reference a static string/HashedString object
    # whose data member points at the literal. Include those indirections in
    # the xref set so the diagnostic finds both direct and object-mediated use.
    indirect_targets: dict[int, str] = {}
    frontier = dict(targets)
    for depth in range(2):
        next_frontier: dict[int, str] = {}
        for section in binary.sections:
            data = section_bytes(section)
            base = section_address(binary, section)
            for target, label in frontier.items():
                encoded = struct.pack("<Q", target)
                start = 0
                while True:
                    offset = data.find(encoded, start)
                    if offset < 0:
                        break
                    address = base + offset
                    derived = f"pointer[{depth + 1}] to {label}"
                    if address not in targets and address not in indirect_targets:
                        indirect_targets[address] = derived
                        next_frontier[address] = derived
                        print(
                            f"POINTER depth={depth + 1} section={section.name} "
                            f"va=0x{address:x} target=0x{target:x} label={label!r}"
                        )
                    start = offset + 1
        frontier = next_frontier
        if not frontier:
            break

    all_targets = {**targets, **indirect_targets}

    print(f"XREF SCAN range=0x{text_address:x}-0x{text_address + len(text_data):x}")
    references: list[tuple[int, int, str]] = []
    seen_references: set[tuple[int, int]] = set()

    # A full Capstone materialization of BDS's very large .text section is
    # needlessly memory hungry. Scan common RIP-relative memory opcodes first,
    # then disassemble only the small windows that actually hit our targets.
    # ModRM mod=00,r/m=101 denotes [RIP+disp32] in 64-bit mode.
    for opcode in (0x8D, 0x8B, 0x89, 0x3B, 0x39, 0x85, 0xFF):
        marker = bytes((opcode,))
        offset = 0
        while True:
            offset = text_data.find(marker, offset)
            if offset < 0:
                break
            if offset + 6 <= len(text_data):
                modrm = text_data[offset + 1]
                if modrm & 0xC7 == 0x05:
                    displacement = struct.unpack_from("<i", text_data, offset + 2)[0]
                    address = text_address + offset + 6 + displacement
                    for target, label in all_targets.items():
                        extent = len(label) if target in targets else 0
                        instruction_address = text_address + offset
                        key = (instruction_address, target)
                        if target <= address <= target + extent and key not in seen_references:
                            seen_references.add(key)
                            references.append((instruction_address, target, label))
            offset += 1

    if not references:
        raise SystemExit("no direct .text references to the requested strings were found")

    for number, (instruction_address, target, label) in enumerate(references, 1):
        if args.reference_number is not None and number != args.reference_number:
            continue
        print(
            f"\nREFERENCE {number} string={label!r} target=0x{target:x} "
            f"instruction=0x{instruction_address:x}"
        )
        function_range = containing_range(function_ranges, instruction_address)
        if function_range:
            function_start, function_end = function_range
            print(
                f"FUNCTION start=0x{function_start:x} end=0x{function_end:x} "
                f"size=0x{function_end - function_start:x}"
            )
            relative = instruction_address - text_address
            window_start = max(0, function_start - text_address)
            window_end = min(len(text_data), function_end - text_address)
        else:
            relative = instruction_address - text_address
            window_start = max(0, relative - max(256, args.context * 10))
            window_end = min(len(text_data), relative + max(384, args.context * 12))
        nearby_instructions = list(
            disassembler.disasm(
                text_data[window_start:window_end], text_address + window_start
            )
        )
        exact_index = next(
            (
                index
                for index, nearby in enumerate(nearby_instructions)
                if nearby.address <= instruction_address < nearby.address + nearby.size
            ),
            None,
        )
        if exact_index is None:
            print("  [unable to align context window]")
            continue
        lower = max(0, exact_index - args.context)
        upper = min(len(nearby_instructions), exact_index + args.context + 1)
        for nearby in nearby_instructions[lower:upper]:
            marker = (
                ">"
                if nearby.address <= instruction_address < nearby.address + nearby.size
                else " "
            )
            print(
                f"{marker} 0x{nearby.address:x}: {nearby.mnemonic:<9} {nearby.op_str}"
            )


if __name__ == "__main__":
    main()
