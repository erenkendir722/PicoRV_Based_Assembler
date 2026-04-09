# opcode_table.py
# RV32I Komut Seti - OPTAB (Opcode Table)
# Her komut için: format tipi, opcode, funct3, funct7

OPTAB = {

    # ─────────────────────────────────────────
    # R-TYPE  |  opcode = 0x33
    # Format: funct7 | rs2 | rs1 | funct3 | rd | opcode
    # ─────────────────────────────────────────
    'ADD':  {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x0, 'funct7': 0x00},
    'SUB':  {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x0, 'funct7': 0x20},
    'SLL':  {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x1, 'funct7': 0x00},
    'SLT':  {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x2, 'funct7': 0x00},
    'SLTU': {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x3, 'funct7': 0x00},
    'XOR':  {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x4, 'funct7': 0x00},
    'SRL':  {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x5, 'funct7': 0x00},
    'SRA':  {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x5, 'funct7': 0x20},
    'OR':   {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x6, 'funct7': 0x00},
    'AND':  {'fmt': 'R', 'opcode': 0x33, 'funct3': 0x7, 'funct7': 0x00},

    # ─────────────────────────────────────────
    # I-TYPE (Aritmetik)  |  opcode = 0x13
    # Format: imm[11:0] | rs1 | funct3 | rd | opcode
    # ─────────────────────────────────────────
    'ADDI':  {'fmt': 'I', 'opcode': 0x13, 'funct3': 0x0},
    'SLTI':  {'fmt': 'I', 'opcode': 0x13, 'funct3': 0x2},
    'SLTIU': {'fmt': 'I', 'opcode': 0x13, 'funct3': 0x3},
    'XORI':  {'fmt': 'I', 'opcode': 0x13, 'funct3': 0x4},
    'ORI':   {'fmt': 'I', 'opcode': 0x13, 'funct3': 0x6},
    'ANDI':  {'fmt': 'I', 'opcode': 0x13, 'funct3': 0x7},

    # I-TYPE (Shift Immediate)  |  opcode = 0x13
    # imm[11:5] = funct7, imm[4:0] = shamt
    'SLLI': {'fmt': 'IS', 'opcode': 0x13, 'funct3': 0x1, 'funct7': 0x00},
    'SRLI': {'fmt': 'IS', 'opcode': 0x13, 'funct3': 0x5, 'funct7': 0x00},
    'SRAI': {'fmt': 'IS', 'opcode': 0x13, 'funct3': 0x5, 'funct7': 0x20},

    # ─────────────────────────────────────────
    # I-TYPE (Load)  |  opcode = 0x03
    # ─────────────────────────────────────────
    'LB':  {'fmt': 'I', 'opcode': 0x03, 'funct3': 0x0},
    'LH':  {'fmt': 'I', 'opcode': 0x03, 'funct3': 0x1},
    'LW':  {'fmt': 'I', 'opcode': 0x03, 'funct3': 0x2},
    'LBU': {'fmt': 'I', 'opcode': 0x03, 'funct3': 0x4},
    'LHU': {'fmt': 'I', 'opcode': 0x03, 'funct3': 0x5},

    # ─────────────────────────────────────────
    # I-TYPE (JALR)  |  opcode = 0x67
    # ─────────────────────────────────────────
    'JALR': {'fmt': 'I', 'opcode': 0x67, 'funct3': 0x0},

    # ─────────────────────────────────────────
    # I-TYPE (Sistem)  |  opcode = 0x73
    # ─────────────────────────────────────────
    'ECALL':  {'fmt': 'SYS', 'opcode': 0x73, 'funct3': 0x0, 'imm': 0x000},
    'EBREAK': {'fmt': 'SYS', 'opcode': 0x73, 'funct3': 0x0, 'imm': 0x001},

    # ─────────────────────────────────────────
    # S-TYPE (Store)  |  opcode = 0x23
    # Format: imm[11:5] | rs2 | rs1 | funct3 | imm[4:0] | opcode
    # ─────────────────────────────────────────
    'SB': {'fmt': 'S', 'opcode': 0x23, 'funct3': 0x0},
    'SH': {'fmt': 'S', 'opcode': 0x23, 'funct3': 0x1},
    'SW': {'fmt': 'S', 'opcode': 0x23, 'funct3': 0x2},

    # ─────────────────────────────────────────
    # B-TYPE (Branch)  |  opcode = 0x63
    # Format: imm[12|10:5] | rs2 | rs1 | funct3 | imm[4:1|11] | opcode
    # ─────────────────────────────────────────
    'BEQ':  {'fmt': 'B', 'opcode': 0x63, 'funct3': 0x0},
    'BNE':  {'fmt': 'B', 'opcode': 0x63, 'funct3': 0x1},
    'BLT':  {'fmt': 'B', 'opcode': 0x63, 'funct3': 0x4},
    'BGE':  {'fmt': 'B', 'opcode': 0x63, 'funct3': 0x5},
    'BLTU': {'fmt': 'B', 'opcode': 0x63, 'funct3': 0x6},
    'BGEU': {'fmt': 'B', 'opcode': 0x63, 'funct3': 0x7},

    # ─────────────────────────────────────────
    # U-TYPE  |  Format: imm[31:12] | rd | opcode
    # ─────────────────────────────────────────
    'LUI':   {'fmt': 'U', 'opcode': 0x37},
    'AUIPC': {'fmt': 'U', 'opcode': 0x17},

    # ─────────────────────────────────────────
    # J-TYPE  |  opcode = 0x6F
    # Format: imm[20|10:1|11|19:12] | rd | opcode
    # ─────────────────────────────────────────
    'JAL': {'fmt': 'J', 'opcode': 0x6F},
}

# Register isimleri → register numarası (ABI isimleri dahil)
REGISTERS = {
    # Sayısal isimler
    'x0': 0,  'x1': 1,  'x2': 2,  'x3': 3,
    'x4': 4,  'x5': 5,  'x6': 6,  'x7': 7,
    'x8': 8,  'x9': 9,  'x10': 10, 'x11': 11,
    'x12': 12, 'x13': 13, 'x14': 14, 'x15': 15,
    'x16': 16, 'x17': 17, 'x18': 18, 'x19': 19,
    'x20': 20, 'x21': 21, 'x22': 22, 'x23': 23,
    'x24': 24, 'x25': 25, 'x26': 26, 'x27': 27,
    'x28': 28, 'x29': 29, 'x30': 30, 'x31': 31,
    # ABI isimleri
    'zero': 0,
    'ra':   1,
    'sp':   2,
    'gp':   3,
    'tp':   4,
    't0':   5,  't1': 6,   't2': 7,
    's0':   8,  'fp': 8,
    's1':   9,
    'a0':  10,  'a1': 11,
    'a2':  12,  'a3': 13,  'a4': 14,  'a5': 15,
    'a6':  16,  'a7': 17,
    's2':  18,  's3': 19,  's4': 20,  's5': 21,
    's6':  22,  's7': 23,  's8': 24,  's9': 25,
    's10': 26,  's11': 27,
    't3':  28,  't4': 29,  't5': 30,  't6': 31,
}

# Desteklenen direktifler
DIRECTIVES = {'.text', '.data', '.word', '.byte', '.org', '.end', '.global', '.extern'}


def get_instruction(mnemonic: str) -> object:
    """Mnemonic'e göre OPTAB'tan komut bilgisini döndürür."""
    return OPTAB.get(mnemonic.upper())


def get_register(name: str) -> object:
    """Register adını numarasına çevirir."""
    return REGISTERS.get(name.lower())


def is_directive(token: str) -> bool:
    """Verilen token bir direktif mi?"""
    return token.lower() in DIRECTIVES


if __name__ == '__main__':
    # Basit test
    print("=== OPTAB Test ===")
    for mnemonic in ['ADD', 'ADDI', 'LW', 'SW', 'BEQ', 'JAL', 'LUI', 'ECALL']:
        info = get_instruction(mnemonic)
        print(f"{mnemonic:<8} → {info}")

    print("\n=== Register Test ===")
    for reg in ['x0', 'zero', 'ra', 'sp', 'a0', 't0', 's0']:
        print(f"{reg:<6} → x{get_register(reg)}")
