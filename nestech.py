"""NES programming library
    
    A library of code intended for use with NES related programming. The only
    current code is intended for use with a disassembler.
"""

# 2007.06.02: v0.0 - initial version

class iNes:
    """Defines an iNES header"""
    initialized = False
    prg_banks = 0
    chr_banks = 0
    mapper = 0
    vram_layout = 0
    trainer_present = False
    battery_present = False
    mirroring = ''
    pc10 = False
    vs_unisystem = False
    ram_pages = 0
    prg_size = 0
    chr_size = 0
    ram_size = 0

    # data should be a string with the header data at the beginning
    def __init__(self, data):
        if not self.valid_ines_tag(data):
            self.initialized = False
            return


        self.prg_banks = data[0x4]
        self.prg_size = self.prg_banks * 0x4000
        self.chr_banks = data[0x5]
        self.chr_size = self.chr_banks * 0x2000
        self.ram_pages = data[0x8]
        self.ram_size = self.ram_pages * 0x2000
        self.mapper = (data[0x7] & 0xf0) | ((data[0x6] & 0xf0) >> 4)
        self.vram_layout = (data[0x6] & 0x08) >> 3

        if data[0x6] & 0x04:
            self.trainer_present = True
        else:
            self.trainer_present = False

        if data[0x6] & 0x02:
            self.battery_present = True
        else:
            self.battery_present = False

        if data[0x6] & 0x01:
            self.mirroring = 'vertical'
        else:
            self.mirroring = 'horizontal'

        if data[0x7] & 0x02:
            self.pc10 = True
        else:
            self.pc10 = False

        if data[0x7] & 0x01:
            self.vs_unisystem = True
        else:
            self.vs_unisystem = False

        self.initialized = True

    def valid_ines_tag(self, data):
        if data[0:4] == [ord('N'),ord('E'),ord('S'), 0x1a]:
            return True
        else:
            return False


class CpuAddrMode:
    """Defines length and argument display for a 6502 instruction"""
    length = 0
    arg = None
    name = ""
    def __init__(self, name, length, arg):
        self.name = name
        self.length = length
        self.arg = arg

    def get_arg(self, mem):
        return self.arg(mem)

    def get_length(self):
        return self.length

    def get_name(self):
        return self.name

    def set_arg(self, arg):
        self.arg = arg

    def set_length(self, length):
        self.length = length

    def set_name(self, name):
        self.name = name
        

def rel_addr(pc, data):
    if data[pc+1] & 0x80:
        return pc + 2 - (256 - data[pc+1])
    else:
        return pc + 2 + data[pc+1]

def abs_addr(pc, data):
    #print "debug %04x" % ((data[pc+1] & 0xff) | ((data[pc+2] & 0xff) << 8))
    return (data[pc+1] & 0xff) | ((data[pc+2] & 0xff) << 8) 


# note, accumulator mode is counted as implied mode

# 0x0 = implied 
# 0x1 = immediate
# 0x2 = zero page
# 0x3 = zero page x
# 0x4 = zero page y
# 0x5 = relative
# 0x6 = absolute
# 0x7 = absolute x
# 0x8 = absolute y
# 0x9 = indirect
# 0xa = indirect x
# 0xb = indirect y
# 0xc = undefined 

cpu_addr_modes = [
    CpuAddrMode('implied',      0,  lambda p,m: ''                              ),
    CpuAddrMode('immediate',    1,  lambda p,m: '#$%02x' % m[p+1]               ),
    CpuAddrMode('zero page',    1,  lambda p,m: '$%02x' % m[p+1]                ),
    CpuAddrMode('zero page x',  1,  lambda p,m: '$%02x,x' % m[p+1]              ),
    CpuAddrMode('zero page y',  1,  lambda p,m: '$%02x,y' % m[p+1]              ),
    CpuAddrMode('relative',     1,  lambda p,m: '$%04x' % rel_addr(p, m)        ),
    CpuAddrMode('absolute',     2,  lambda p,m: '$%04x' % (abs_addr(p, m))      ),
    CpuAddrMode('absolute x',   2,  lambda p,m: '$%04x,x' % (abs_addr(p, m))    ),
    CpuAddrMode('absolute y',   2,  lambda p,m: '$%04x,y' % (abs_addr(p, m))    ),
    CpuAddrMode('indirect',     2,  lambda p,m: '($%04x)' % (abs_addr(p, m))    ),
    CpuAddrMode('indirect x',   1,  lambda p,m: '($%02x,x)' % m[p+1]            ),
    CpuAddrMode('indirect y',   1,  lambda p,m: '($%02x),y' % m[p+1]            ),
    CpuAddrMode('undefined',    0,  lambda p,m: ''                              ),
]


cpu_opcodes = [
    # 0x00
    ('brk',0x0),('ora',0xa),('und',0xc),('und',0xc),
    ('und',0xc),('ora',0x2),('asl',0x2),('und',0xc),
    ('php',0x0),('ora',0x1),('asl',0x0),('und',0xc),
    ('und',0xc),('ora',0x6),('asl',0x6),('und',0xc),
    # 0x10
    ('bpl',0x5),('ora',0xb),('und',0xc),('und',0xc),
    ('und',0xc),('ora',0x3),('asl',0x3),('und',0xc),
    ('clc',0x0),('ora',0x8),('und',0xc),('und',0xc),
    ('und',0xc),('ora',0x7),('asl',0x7),('und',0xc),
    # 0x20
    ('jsr',0x6),('and',0xa),('und',0xc),('und',0xc),
    ('bit',0x2),('and',0x2),('rol',0x2),('und',0xc),
    ('plp',0x0),('and',0x1),('rol',0x0),('und',0xc),
    ('bit',0x2),('and',0x6),('rol',0x6),('und',0xc),
    # 0x30
    ('bmi',0x5),('and',0xb),('und',0xc),('und',0xc),
    ('und',0xc),('and',0x3),('rol',0x3),('und',0xc),
    ('sec',0x0),('and',0x8),('und',0xc),('und',0xc),
    ('und',0xc),('and',0x7),('rol',0x7),('und',0xc),
    # 0x40
    ('rti',0x0),('eor',0xa),('und',0xc),('und',0xc),
    ('und',0xc),('eor',0x2),('lsr',0x2),('und',0xc),
    ('pha',0x0),('eor',0x1),('lsr',0x0),('und',0xc),
    ('jmp',0x6),('eor',0x6),('lsr',0x6),('und',0xc),
    # 0x50
    ('bvc',0x5),('eor',0xb),('und',0xc),('und',0xc),
    ('und',0xc),('eor',0x3),('lsr',0x3),('und',0xc),
    ('cli',0x0),('eor',0x8),('und',0xc),('und',0xc),
    ('und',0xc),('eor',0x7),('lsr',0x7),('und',0xc),
    # 0x60
    ('rts',0x0),('adc',0xa),('und',0xc),('und',0xc),
    ('und',0xc),('adc',0x2),('ror',0x2),('und',0xc),
    ('pla',0x0),('adc',0x1),('ror',0x0),('und',0xc),
    ('jmp',0x9),('adc',0x6),('ror',0x6),('und',0xc),
    # 0x70
    ('bvs',0x5),('adc',0xb),('und',0xc),('und',0xc),
    ('und',0xc),('adc',0x3),('ror',0x3),('und',0xc),
    ('sei',0x0),('adc',0x8),('und',0xc),('und',0xc),
    ('und',0xc),('adc',0x7),('ror',0x7),('und',0xc),
    # 0x80
    ('und',0xc),('sta',0xa),('und',0xc),('und',0xc),
    ('sty',0x2),('sta',0x2),('stx',0x2),('und',0xc),
    ('dey',0x0),('und',0xc),('txa',0x0),('und',0xc),
    ('sty',0x6),('sta',0x6),('stx',0x6),('und',0xc),
    # 0x90
    ('bcc',0x5),('sta',0xb),('und',0xc),('und',0xc),
    ('sty',0x3),('sta',0x3),('stx',0x4),('und',0xc),
    ('tya',0x0),('sta',0x8),('txs',0x0),('und',0xc),
    ('und',0xc),('sta',0x7),('und',0xc),('und',0xc),
    # 0xa0
    ('ldy',0x1),('lda',0xa),('ldx',0x1),('und',0xc),
    ('ldy',0x2),('lda',0x2),('ldx',0x2),('und',0xc),
    ('tay',0x0),('lda',0x1),('tax',0x0),('und',0xc),
    ('ldy',0x6),('lda',0x6),('ldx',0x6),('und',0xc),
    # 0xb0
    ('bcs',0x5),('lda',0xb),('und',0xc),('und',0xc),
    ('ldy',0x3),('lda',0x3),('ldx',0x4),('und',0xc),
    ('clv',0x0),('lda',0x8),('tsx',0x0),('und',0xc),
    ('ldy',0x7),('lda',0x7),('ldx',0x8),('und',0xc),
    # 0xc0
    ('cpy',0x1),('cmp',0xa),('und',0xc),('und',0xc),
    ('cpy',0x2),('cmp',0x2),('dec',0x2),('und',0xc),
    ('iny',0x0),('cmp',0x1),('dex',0x0),('und',0xc),
    ('cpy',0x6),('cmp',0x6),('dec',0x6),('und',0xc),
    # 0xd0
    ('bne',0x5),('cmp',0xb),('und',0xc),('und',0xc),
    ('und',0xc),('cmp',0x3),('dec',0x3),('und',0xc),
    ('cld',0x0),('cmp',0x8),('und',0xc),('und',0xc),
    ('und',0xc),('cmp',0x7),('dec',0x7),('und',0xc),
    # 0xe0
    ('cpx',0x1),('sbc',0xa),('und',0xc),('und',0xc),
    ('cpx',0x2),('sbc',0x2),('inc',0x2),('und',0xc),
    ('inx',0x0),('sbc',0x1),('nop',0x0),('und',0xc),
    ('cpx',0x6),('sbc',0x6),('inc',0x6),('und',0xc),
    # 0xf0
    ('beq',0x5),('sbc',0xb),('und',0xc),('und',0xc),
    ('und',0xc),('sbc',0x3),('inc',0x3),('und',0xc),
    ('sed',0x0),('sbc',0x8),('und',0xc),('und',0xc),
    ('und',0xc),('sbc',0x7),('inc',0x7),('und',0xc)
]
