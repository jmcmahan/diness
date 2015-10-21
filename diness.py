#!/usr/bin/env python

# diness - NES oriented 6502 disassembler. 
# author: J. A. McMahan Jr.
#
# 2007.09.18: v0.4 - Fixed a bug where a stray label would be added when switching
#                    from code to data after a data byte that had a label due to an
#                    absolute reference
#
# 2007.06.07: v0.3 - Added labels for absolute and absolute indexed addresses
#                    within the program ROM range.
#
# 2007.06.06: v0.2 - The missing code is probably due to jump tables and other
#                    hard to automatically identify techniques for changing the
#                    PC. I added in a simple labeling method, so it may be
#                    possible to actually reassemble the file.
#
#                    Ideas for possible future improvements:
#                    1) Possibly add labels for absolute and absolute indexed
#                       addresses that are within the program ROM range.
#                    2) Add defined variables to top of the assembly file, for 
#                       RAM locations that are accessed directly in the file.
#                    3) Add option to specify code entry points through a separate
#                       file or on the commandline.
#                    4) Add commandline options to control various ways of 
#                       outputting the data.
#                    5) Add support for automatically disassembling other mappers,
#                       besides just mapper 0 (if possible).
#                    6) Add option to automatically dump out the CHR-ROM as 
#                       binary or data files, to make reassembly easier.
#                    7) Optional comments and such for known memory mapped 
#                       registers.
#                    8) Maybe add searches for loops that are known to setup
#                       absolute addresses in the program ROM space, so labels
#                       can be added for them, as well.
#                    9) Possibly add ability to disassemble code in ".byte"
#                       directives, to simplify getting code that's been missed.
#                    10) If the statistics can be found or computed, implement 
#                       some sort of code that marks bytes as code, based on 
#                       the statistical likelihood of the surrounding bytes 
#                       also being code
#                    11) Organize the code better
#
# 2007.06.05: v0.1 - fixed some of the problems with it finding code. Part of
#                    it was the relative addressing being done incorrectly. It
#                    now correctly disassembles all the used code in a demo 
#                    game. Still missing code in commercial games, though.
#
# 2007.06.05: v0.0 - initial version number, basic disassembly works, but 
#                    seems as though it may be missing a lot of code.
#



import sys
import nestech


supported_mappers = [0]

branches = [0x10, 0x30, 0x50, 0x70, 0x90, 0xb0, 0xd0, 0xf0]
jump_indirect = [0x6c]
jump_absolute = [0x4c]
jsr = [0x20]
return_ops = [0x40, 0x60]


redir_ops = branches + jump_absolute + jsr




def error_exit(message):
    """Prints an error message before exiting"""
    print message
    sys.exit(-1)

def word_from_bytes(data):
    """Takes an array of two bytes and makes a 16-bit word from it"""
    return (data[0] & 0xff) | ((data[1] & 0xff) << 8)

def trace_code(pc, data, marks, points, labels):
    """Follows a line of code until an unconditional branch or invalid opcode"""

    while not marks[pc]:
        op = data[pc]
        opinfo = nestech.cpu_opcodes[op]
        length = 1 + nestech.cpu_addr_modes[opinfo[1]].get_length()
        mneumonic = opinfo[0]
        

        if op in branches:
            marks[pc] = True
            if not marks[nestech.rel_addr(pc, data)]:
                points.insert(0,nestech.rel_addr(pc, data))
            if not nestech.rel_addr(pc, data) in labels:
                labels.insert(0,nestech.rel_addr(pc, data))
            pc += length

        elif op in jsr:
            marks[pc] = True
            if not marks[nestech.abs_addr(pc, data)]:
                points.insert(0,nestech.abs_addr(pc, data))
            if not nestech.abs_addr(pc, data) in labels:
                labels.insert(0,nestech.abs_addr(pc, data))
            pc += length

        elif op in jump_absolute:
            marks[pc] = True
            if not marks[nestech.abs_addr(pc, data)]:
                points.insert(0,nestech.abs_addr(pc, data))
            if not nestech.abs_addr(pc, data) in labels:
                labels.insert(0,nestech.abs_addr(pc, data))
            return

        elif op in jump_indirect:
            marks[pc] = True
            return

        elif op in return_ops:
            marks[pc] = True
            return

        elif not mneumonic == 'und':
            addr_mode = nestech.cpu_addr_modes[opinfo[1]].get_name()
            # may change to 'absolute ' if want to just do indexed
            if 'absolute' in addr_mode:
                addr = nestech.abs_addr(pc, data)
                if 0x8000 <= addr and addr <= 0xffff:
                    labels.insert(0,addr)
            marks[pc] = True
            pc += length
        else:
            return 


if len(sys.argv) != 2:
    error_exit('Missing input file')
input_file = sys.argv[1]

output_file = sys.stdout


try:
    f = open(input_file, 'rb')
except:
    error_exit('Error opening file: %s' % input_file)

rom_data = [ ord(i) for i in f.read() ]
f.close()

rom_hdr = nestech.iNes(rom_data)

if not rom_hdr.initialized:
    error_exit('Unrecognized file format: %s\n' % input_file)

if not rom_hdr.mapper in supported_mappers:
    error_exit('Mapper %d not currently supported\n' % rom_hdr.mapper)    


prg_size = rom_hdr.prg_size

# Move program data to end of 65536 byte array to make addressing easier.
# Note this only works for roms with no mapper, so make sure to change this
# when adding support for others.
prg_data = (0x10000 - rom_hdr.prg_size) * [0] +     \
           rom_data[0x10:0x10 + rom_hdr.prg_size]

brk_addr = word_from_bytes(prg_data[-2:  ])
rst_addr = word_from_bytes(prg_data[-4:-2])
nmi_addr = word_from_bytes(prg_data[-6:-4])


# Find code
code_marks = 0x10000 * [False]
named_labels = {brk_addr:'irq', rst_addr:'reset', nmi_addr:'nmi'}
code_points = [brk_addr, rst_addr, nmi_addr]
labels = [brk_addr, rst_addr, nmi_addr]



while code_points:
    pc = code_points.pop()
    trace_code(pc, prg_data, code_marks, code_points, labels)


# Disassemble and display code and data
j = 0
pc = 0x10000 - rom_hdr.prg_size

prev_type = {'code':True, 'data':True}

while pc < 0x10000:
    if pc in labels:
        j = 0
        if named_labels.has_key(pc):
            output_file.write('\n\n%s:\n' % named_labels[pc])
        else:
            output_file.write('\n\nL%04X:\n' % pc)
        label_done = True
    else:
        label_done = False
    # data
    if not code_marks[pc]:
        # do a label when switching from code to data
        if not label_done and prev_type['code']:
            output_file.write('\n\nL%04X:\n' % pc)
            label_done = True
            prev_type['code'] = False
            prev_type['data'] = True
        elif label_done and prev_type['code']:
            prev_type['code'] = False
            prev_type['data'] = True
            
        data_string = '$%02x' % prg_data[pc]
        if not j % 16:
            output_file.write('.byte %s' % (data_string))
        elif j % 16 == 15:
            output_file.write(',' + data_string + '\n')
        else:
            output_file.write(',' + data_string)
        j += 1 
        pc += 1
    # code
    else:
        if not label_done and prev_type['data']:
            output_file.write('\n\nL%04X:\n' % pc)
            label_done = True
            prev_type['code'] = True
            prev_type['data'] = False
        if j % 16:
            j = 0
            if not label_done:
                output_file.write('\n\n')

        op = prg_data[pc]
        opinfo = nestech.cpu_opcodes[op]
        length = 1 + nestech.cpu_addr_modes[opinfo[1]].get_length()
        mneumonic = opinfo[0]
        arg = nestech.cpu_addr_modes[opinfo[1]].arg(pc, prg_data)
        addr_mode = nestech.cpu_addr_modes[opinfo[1]].get_name()

        if op in redir_ops:
            if named_labels.has_key(int(arg[1:], 16)):
                arg = named_label[int(arg[1:], 16)]
                code_string = 4*' ' + mneumonic  + ' ' + arg 
                code_string += (16-len(arg))*' ' + '; $%04x' % (pc)
            else:
                arg = arg[1:].upper()
                code_string = 4*' ' + mneumonic  + ' ' + 'L' + arg 
                code_string += 11*' ' + '; $%04x' % (pc)

        elif 'absolute' in addr_mode:
            if named_labels.has_key(int(arg[1:5], 16)):
                arg = named_label[int(arg[1:], 16)]
                code_string = 4*' ' + mneumonic + ' ' +  arg 
                code_string += (16-len(arg))*' ' + '; $%04x' % (pc)
            elif nestech.abs_addr(pc, prg_data) in labels:
                arg = arg[1:5].upper() + arg[5:]
                code_string = 4*' ' + mneumonic + ' ' + 'L' + arg 
                code_string += (16 - len(arg) - 1)*' ' + '; $%04x' % (pc)
            else:
                code_string = 4*' ' + mneumonic + ' ' + arg 
                code_string += (16 - len(arg))*' ' + '; $%04x' % (pc)

        else:
            code_string = 4*' ' + mneumonic  + ' ' + arg 
            code_string += (16 - len(arg))*' ' + '; $%04x' % (pc)

        output_file.write(code_string + '\n')
        pc += length

output_file.write('\n\n')


