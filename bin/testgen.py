#!/usr/bin/env python3
##################################
# testgen.py
#
# David_Harris@hmc.edu 27 March 2024
#
# Generate directed tests for functional coverage
##################################

##################################
# libraries
##################################
from datetime import datetime
from random import randint 
from random import seed
from random import getrandbits
import os
import re

##################################
# functions
##################################

def shiftImm(imm, xlen):
  imm = imm % xlen
  return str(imm)

def signedImm12(imm):
  imm = imm % pow(2, 12)
  if (imm & 0x800):
    imm = imm - 0x1000
  return str(imm)

def unsignedImm20(imm):
  imm = imm % pow(2, 20)
  return str(imm)

def writeCovVector(desc, rs1, rs2, rd, rs1val, rs2val, immval, rdval, test, xlen):
  lines = "\n# Testcase " + str(desc) + "\n"
  if (rs1val < 0):
    rs1val = rs1val + 2**xlen
  if (rs2val < 0):
    rs2val = rs2val + 2**xlen
  lines = lines + "li x" + str(rd) + ", " + formatstr.format(rdval) + " # initialize rd to a random value that should get changed; helps covering rd_toggle\n"
  if (test in rtype):
    lines = lines + "li x" + str(rs1) + ", " + formatstr.format(rs1val) + " # initialize rs1\n"
    lines = lines + "li x" + str(rs2) + ", " + formatstr.format(rs2val) + " # initialize rs2\n"
    lines = lines + test + " x" + str(rd) + ", x" + str(rs1) + ", x" + str(rs2) + " # perform operation\n" 
  elif (test in shiftitype):
    lines = lines + "li x" + str(rs1) + ", " + formatstr.format(rs1val) + " # initialize rs1\n"
    if (test in shiftiwtype):
      lines = lines + test + " x" + str(rd) + ", x" + str(rs1) + ", " + shiftImm(immval, 32) + " # perform operation\n"
    else:
      lines = lines + test + " x" + str(rd) + ", x" + str(rs1) + ", " + shiftImm(immval, xlen) + " # perform operation\n"
  elif (test in itype):
    lines = lines + "li x" + str(rs1) + ", " + formatstr.format(rs1val) + " # initialize rs1\n"
    lines = lines + test + " x" + str(rd) + ", x" + str(rs1) + ", " + signedImm12(immval) + " # perform operation\n"
  elif (test in loaditype):#["lb", "lh", "lw", "ld", "lbu", "lhu", "lwu"]
    if (rs1 != 0):
      lines = lines + "li x" + str(rs2) + ", " + formatstr.format(rs2val)  + " # initialize rs2\n"
      lines = lines + "la x" + str(rs1) + ", scratch" + " # base address \n"
      lines = lines + "addi x" + str(rs1) + ", x" + str(rs1) + ", " + signedImm12(-immval) + " # sub immediate from rs1 to counter offset\n"
      if (xlen == 32):
        storeop = "sw"
      else:
        storeop = "sd"
      lines = lines + storeop + " x" + str(rs2) + ", " + signedImm12(immval) +" (x" + str(rs1) + ") # store value to put someting in memory\n"
      lines = lines + test + " x" + str(rd) + ", " + signedImm12(immval) + "(x" + str(rs1) + ") # perform operation\n"
#      lines = lines + test + " x" + str(rd) + ", 0(x" + str(rs1) + ") # perform operation\n"
  elif (test in stype):#["sb", "sh", "sw", "sd"]
    if (rs1 != 0):
      if (rs2 == rs1): # make sure registers are different so they don't conflict
          rs2 = (rs1 + 1) % 32
          if (rs2 == 0):
            rs2 = 1
      lines = lines + "li x" + str(rs2) + ", " + formatstr.format(rs2val)  + " # initialize rs2\n"
      lines = lines + "la x" + str(rs1) + ", scratch" + " # base address \n"
      lines = lines + "addi x" + str(rs1) + ", x" + str(rs1) + ", " + signedImm12(-immval) + " # sub immediate from rs1 to counter offset\n"
      lines = lines + test + " x" + str(rs2) + ", " + signedImm12(immval) + "(x" + str(rs1) + ") # perform operation \n"
  elif (test in btype):#["beq", "bne", "blt", "bge", "bltu", "bgeu"]
    for same in range(2):
      if (same):
        rs1val = rs2val
        lines = lines + "# same values in both registers\n"
      lines = lines + "nop\n"
      lines = lines + "li x" + str(rs1) + ", " + formatstr.format(rs1val) + " # initialize rs1\n"
      lines = lines + "li x" + str(rs2) + ", " + formatstr.format(rs2val) + " # initialize rs2\n"
      lines = lines + test + " x" + str(rs1) + ", x" + str(rs2) + ", some_label_for_btype_" + str(immval) + str(same) + " # perform operation \n"
      lines = lines + "addi x0, x1, 1\n"
      lines = lines + "some_label_for_btype_" + str(immval)+ str(same) + ":\n"
      lines = lines + "addi x0, x2, 2\n"
      lines = lines + "nop\nnop\nnop\nnop\nnop\n"
  elif (test in jtype):#["jal"]
    lines = lines + "jal x" + str(rd) + ", 1f # perform operation\n"
    lines = lines + "nop\n"
    lines = lines + "1:\n"
  elif (test in jalrtype):#["jalr"]
    lines = lines + "la x" + str(rs1) + ", 1f\n"
    lines = lines + "addi x" + str(rs1) + ", x" + str(rs1) + ", " + signedImm12(-immval) + " # add immediate to lower part of rs1\n"
    lines = lines + "jalr x" + str(rd) + ", x" + str(rs1) + ", " + signedImm12(immval) + " # perform operation\n"
    lines = lines + "nop\n"
    lines = lines + "1:\n"
  elif (test in utype):#["lui", "auipc"]
    lines = lines + test + " x" + str(rd) + ", " + unsignedImm20(immval) + " # perform operation\n"
  else:
    pass
    #print("Error: %s type not implemented yet" % test)
  f.write(lines)

def writeHazardVector(desc, rs1a, rs2a, rda, rs1b, rs2b, rdb, test):
  # consecutive R-type instructions to trigger hazards
  lines = "\n# Testcase " + str(desc) + "\n"
  lines = lines + test + " x" + str(rda) + ", x" + str(rs1a) + ", x" + str(rs2a) + " # perform first operation\n" 
  lines = lines + test + " x" + str(rdb) + ", x" + str(rs1b) + ", x" + str(rs2b) + " # perform second operation\n" 
  f.write(lines)

def randomize():
    rs1 = randint(1, 31)
    rs2 = randint(1, 31)
    # choose rd that is different than rs1 and rs2
    rd = rs1
    while (rd == rs1 or rd == rs2):
      rd = randint(1, 31)
    rd = randint(1, 31)
    rs1val = randint(0, 2**xlen-1)
    rs2val = randint(0, 2**xlen-1)
    immval = randint(0, 2**xlen-1)
    rdval = randint(0, 2**xlen-1)
    return [rs1, rs2, rd, rs1val, rs2val, immval, rdval]

def make_rd(test, xlen):
  for r in range(32):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cp_rd (Test destination rd = x" + str(r) + ")"
    writeCovVector(desc, rs1, rs2, r, rs1val, rs2val, immval, rdval, test, xlen)

def make_rs1(test, xlen):
  for r in range(32):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cp_rs1 (Test source rs1 = x" + str(r) + ")"
    writeCovVector(desc, r, rs2, rd, rs1val, rs2val, immval, rdval, test, xlen)

def make_rs2(test, xlen):
  for r in range(32):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cp_rs2 (Test source rs2 = x" + str(r) + ")"
    writeCovVector(desc, rs1, r, rd, rs1val, rs2val, immval, rdval, test, xlen)

def make_rd_rs1(test, xlen):
  for r in range(32):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cmp_rd_rs1 (Test rd = rs1 = x" + str(r) + ")"
    writeCovVector(desc, r, rs2, r, rs1val, rs2val, immval, rdval, test, xlen)

def make_cp_rs1_nx0(test, xlen):
  for r in range(32):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cp_rs1_nx0 (Test source rs1 = x" + str(r) + ")"
    writeCovVector(desc, r, rs2, rd, rs1val, rs2val, immval, rdval, test, xlen)


def make_rd_rs2(test, xlen):
  for r in range(32):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cmp_rd_rs2 (Test rd = rs1 = x" + str(r) + ")"
    writeCovVector(desc, rs1, r, r, rs1val, rs2val, immval, rdval, test, xlen)

def make_rd_rs1_rs2(test, xlen):
  for r in range(32):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cmp_rd_rs1_rs2 (Test rd = rs1 = rs2 = x" + str(r) + ")"
    writeCovVector(desc, r, r, r, rs1val, rs2val, immval, rdval, test, xlen)

def make_rs1_rs2(test, xlen):
  for r in range(32):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cmp_rs1_rs2 (Test rs1 = rs2 = x" + str(r) + ")"
    writeCovVector(desc, r, r, rd, rs1val, rs2val, immval, rdval, test, xlen)

def make_rs1_corners(test, xlen):
  for v in corners:
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cp_rs1_corners (Test source rs1 value = " + hex(v) + ")"
    writeCovVector(desc, rs1, rs2, rd, v, rs2val, immval, rdval, test, xlen)

def make_rs2_corners(test, xlen):
  for v in corners:
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    desc = "cp_rs2_corners (Test source rs2 value = " + hex(v) + ")"
    writeCovVector(desc, rs1, rs2, rd, rs1val, v, immval, rdval, test, xlen)

def make_rd_corners(test, xlen):
  if (xlen==32):
    for v in corners_32:
      # rs1 = 0, rs2 = v, others are random
      [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
      desc = "cp_rd_corners (Test rd value = " + hex(v) + ")"
      writeCovVector(desc, rs1, 0, rd, v, rs2val, 0, rdval, test, xlen)
      # rs1, rs2 = v, others are random
      [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
      desc = "cp_rd_corners (Test rd value = " + hex(v) + ")"
      writeCovVector(desc, rs1, rs2, rd, v, v, v, rdval, test, xlen)
      # rs1 = all 1s, rs2 = v, others are random
      [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
      desc = "cp_rd_corners (Test rd value = " + hex(v) + ")"
      writeCovVector(desc, rs1, rs2, rd, -1, v, -1, rdval, test, xlen)
  else:
    for v in corners_64:
      # rs1 = 0, rs2 = v, others are random
      [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
      desc = "cp_rd_corners (Test rd value = " + hex(v) + ")"
      writeCovVector(desc, rs1, 0, rd, v, rs2val, 0, rdval, test, xlen)
      # rs1, rs2 = v, others are random
      [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
      desc = "cp_rd_corners (Test rd value = " + hex(v) + ")"
      writeCovVector(desc, rs1, rs2, rd, v, v, v, rdval, test, xlen)
      # rs1 = all 1s, rs2 = v, others are random
      [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
      desc = "cp_rd_corners (Test rd value = " + hex(v) + ")"
      writeCovVector(desc, rs1, rs2, rd, -1, v, -1, rdval, test, xlen)


def make_rd_rs1_eqval(test, xlen):
  [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
  desc = "cmp_rdm_rs1_eqval (Test rs1 = rd = " + hex(rs1val) + ")"
  writeCovVector(desc, rs1, 0, rd, rdval, rs2val, immval, rdval, test, xlen)

def make_rd_rs2_eqval(test, xlen):
  [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
  desc = "cmp_rd_rs2_eqval (Test rs2 = rd = " + hex(rs2val) + ")"
  writeCovVector(desc, 0, rs2, rd, rs1val, rdval, immval, rdval, test, xlen)

def make_rs1_rs2_eqval(test, xlen):
  [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
  desc = "cmp_rs1_rs2_eqval (Test rs1 = rs2 = " + hex(rs1val) + ")"
  writeCovVector(desc, rs1, rs2, rd, rs1val, rs1val, immval, rdval, test, xlen)

def make_cp_gpr_hazard(test, xlen):
  for haz in ["raw", "waw", "war"]:
    for src in range(2):
      [rs1a, rs2a, rda, rs1vala, rs2vala, immvala, rdvala] = randomize()
      [rs1b, rs2b, rdb, rs1valb, rs2valb, immvalb, rdvalb] = randomize()
      # set up hazard
      if (haz == "raw"):
        if (src):
          rs2b = rda
        else:
          rs1b = rda
      elif (haz == "waw"):  
        rdb = rda
      elif (haz == "war"):
        if (src):
          rdb = rs2a
        else:
          rdb = rs1a
      desc = "cmp_gpr_hazard " + haz +  " test"
      writeHazardVector(desc, rs1a, rs2a, rda, rs1b, rs2b, rdb, test)

def make_rs1_sign(test, xlen):
   for v in [1, -1]:
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    rs1val = abs(rs1val % 2**(xlen-1)) * v;
    desc = "cp_rs1_sign (Test source rs1 value = " + hex(rs1val) + ")"
    writeCovVector(desc, rs1, rs2, rd, rs1val, rs2val, immval, rdval, test, xlen)

def make_rs2_sign(test, xlen):
  for v in [1, -1]:
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    rs2val = abs(rs2val % 2**(xlen-1)) * v;
    desc = "cp_rs2_sign (Test source rs2 value = " + hex(rs2val) + ")"
    writeCovVector(desc, rs1, rs2, rd, rs1val, rs2val, immval, rdval, test, xlen)

def make_cr_rs1_rs2_corners(test, xlen):
  for v1 in corners:
    for v2 in corners:
      [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
      desc = "cr_rs1_rs2_corners (Test source rs1 = " + hex(v1) + " rs2 = " + hex(v2) + ")"
      writeCovVector(desc, rs1, rs2, rd, v1, v2, immval, rdval, test, xlen)

def make_imm_zero(test, xlen):
  [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
  desc = "cp_imm_zero"
  writeCovVector(desc, rs1, rs2, rd, rs1val, rs2val, 0, rdval, test, xlen)

def make_j_imm_ones_zeros(test, xlen):
  for align in range(2,19):
    lines = "\n# Testcase cp_imm_ones_zeros " + str(align) + "\n"
    lines = lines + "li x1, " + formatstr.format(randint(0, 2**xlen-1)) + "\n"
    lines = lines + "jal x20, 1f # jump to aligned address to stress immediate\n"
    lines = lines + ".align " + str(align) + "\n"
    lines = lines + "1:\n"
    f.write(lines)

def make_offset(test, xlen):
  if (test in btype):
    lines = "\n# Testcase cp_offset\n"
    lines = lines + "j 2f # jump past backward branch target\n"
    lines = lines + "1: j 3f # backward branch target: jump past backward branch\n"
    lines = lines + "2: " + test + " x0, x0, 1b # backward branch\n"
    lines = lines + "3: nop # done with sequence\n"
    f.write(lines)

def make_mem_hazard(test, xlen):
  lines = "\n# Testcase mem_hazard (no dependency)\n"
  lines = lines + "la x1, scratch\n"
  lines = lines + test + " x2, 0(x1)\n"
  f.write(lines)

def make_cp_imm12_corners(test, xlen):
  desc = "cp_imm12_corners"
  [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
  for v1 in corners_imm:
    writeCovVector(desc, rs1, rs2, rd, rs1val, rs2val, v1, rdval, test, xlen)

def make_cr_rs1_imm_corners(test, xlen):
  desc = "cr_rs1_imm_corners"
  [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
  for v1 in corners:
    for v2 in corners_imm:
      writeCovVector(desc, rs1, rs2, rd, v1, rs2val, v2, rdval, test, xlen)

def make_imm_shift(test, xlen):
  desc = "cp_imm_shift"
  for shift in range(0, xlen):
    [rs1, rs2, rd, rs1val, rs2val, immval, rdval] = randomize()
    writeCovVector(desc, rs1, rs2, rd, rs1val, rs2val, shift, rdval, test, xlen)

def write_tests(coverpoints, test, xlen):
  for coverpoint in coverpoints:
    if (coverpoint == "cp_asm_count"):
      pass
    elif (coverpoint == "cp_rd"):
      make_rd(test, xlen)
    elif (coverpoint == "cp_rs1"):
      make_rs1(test, xlen)
    elif (coverpoint == "cp_rs2"):
      make_rs2(test, xlen)
    elif (coverpoint == "cmp_rd_rs1"):
      make_rd_rs1(test, xlen)
    elif (coverpoint == "cmp_rd_rs2"):
      make_rd_rs2(test, xlen)
    elif (coverpoint == "cmp_rd_rs1_rs2"):
      make_rd_rs1_rs2(test, xlen)
    elif (coverpoint == "cmp_rs1_rs2"):
      make_rs1_rs2(test, xlen)
    elif (coverpoint == "cp_rs1_corners"):
      make_rs1_corners(test, xlen)
    elif (coverpoint == "cp_rs2_corners"):
      make_rs2_corners(test, xlen)
    elif (coverpoint == "cp_rd_corners"):
      make_rd_corners(test, xlen)
    elif (coverpoint == "cp_rs1_nx0"):
      make_cp_rs1_nx0(test, xlen)
    elif (coverpoint == "cmp_rd_rs1_eqval"):
      make_rd_rs1_eqval(test, xlen)
    elif (coverpoint == "cmp_rd_rs2_eqval"):
      make_rd_rs2_eqval(test, xlen)
    elif (coverpoint == "cmp_rs1_rs2_eqval"):
      make_rs1_rs2_eqval(test, xlen)
    elif (coverpoint == "cp_rs1_sign"):
      make_rs1_sign(test, xlen)
    elif (coverpoint == "cp_rs2_sign"):
      make_rs2_sign(test, xlen)
    elif (coverpoint == "cp_rd_sign"):
      pass # already covered by rd_corners
    elif (coverpoint == "cr_rs1_rs2_corners"):
      make_cr_rs1_rs2_corners(test, xlen)
    elif (coverpoint == "cp_imm12_corners"):
      make_cp_imm12_corners(test, xlen)
    elif (coverpoint == "cr_rs1_imm_corners"):
      make_cr_rs1_imm_corners(test, xlen)
    elif (coverpoint == "cr_rs1_rs2"):
      pass # already covered by cr_rs1_rs2_corners
    elif (coverpoint == "cp_gpr_hazard"):
      make_cp_gpr_hazard(test, xlen)
    elif (coverpoint == "cp_rs1_toggle"):
      pass #TODO toggle not needed and seems to be covered by other things
    elif (coverpoint == "cp_rs2_toggle"):
      pass #TODO toggle not needed and seems to be covered by other things
    elif (coverpoint == "cp_rd_toggle"):
      pass #TODO toggle not needed and seems to be covered by other things
    elif (coverpoint == "cp_imm_sign"):
      make_imm_zero(test, xlen)
    elif (coverpoint == "cp_imm_ones_zeros"):
      if (test in jtype):
        make_j_imm_ones_zeros(test, xlen)
    elif (coverpoint == "cp_mem_hazard"):
      make_mem_hazard(test, xlen)
    elif (coverpoint == "cp_imm_zero"):
      make_imm_zero(test, xlen)
    elif (coverpoint == "cp_mem_unaligned"):
      pass # seems this should be part of privileged tests
    elif (coverpoint == "cp_offset"):
      make_offset(test, xlen)
    elif (coverpoint == "cr_nord_rs1_rs2"):
      pass #TODO (not if crosses are not needed)
    elif (coverpoint == "cp_imm_shift"):
      make_imm_shift(test, xlen)
    elif (coverpoint == "cp_rd_boolean"):
      pass # covered by other generators
    else:
      print("Warning: " + coverpoint + " not implemented yet for " + test)
      
def getcovergroups(coverdefdir, coverfiles):
  coverpoints = {}
  curinstr = ""
  for coverfile in coverfiles:
    coverfile = coverdefdir + "/" + coverfile + "_coverage.svh"
    f = open(coverfile, "r")
    for line in f:
      m = re.search(r'cp_asm_count.*\"(.*)"', line)
      if (m):
#        if (curinstr != ""):
#          print(curinstr + ": " + str(coverpoints[curinstr]))
        curinstr = m.group(1)
        coverpoints[curinstr] = []
      m = re.search("\s*(\S+) :", line)
      if (m):
        coverpoints[curinstr].append(m.group(1))
    f.close()
    print(coverpoints)
    return coverpoints

##################################
# main body
##################################

if __name__ == '__main__':
  # change these to suite your tests
  WALLY = os.environ.get('WALLY')
  #coverfiles = ["RV64I", "RV64M", "RV64A", "RV64C", "RV64F", "RV64D"] # add more later
  rtype = ["add", "sub", "sll", "slt", "sltu", "xor", "srl", "sra", "or", "and",
            "addw", "subw", "sllw", "srlw", "sraw"
            "mul", "mulh", "mulhsu", "mulhu", "div", "divu", "rem", "remu",
            "mulw", "divw", "divuw", "remw", "remuw"]
  loaditype = ["lb", "lh", "lw", "ld", "lbu", "lhu", "lwu"]
  shiftitype = ["slli", "srli", "srai", "slliw", "srliw", "sraiw"]
  shiftiwtype = ["slliw", "srliw", "sraiw"]
  itype = ["addi", "slti", "sltiu", "xori", "ori", "andi", "addiw"]
  stype = ["sb", "sh", "sw", "sd"]
  btype = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]
  jtype = ["jal"]
  jalrtype = ["jalr"]
  utype = ["lui", "auipc"]
  # TODO: auipc missing, check whatelse is missing in ^these^ types


  author = "David_Harris@hmc.edu"
  xlens = [32, 64]
  numrand = 3
  corners = []

  # setup
  seed(0) # make tests reproducible

  # generate files for each test
  for xlen in xlens:
    coverdefdir = WALLY+"/addins/cvw-arch-verif/fcov/rv"+str(xlen)+"/coverage"
    coverfiles = ["RV"+str(xlen)+"I"] # add more later
    coverpoints = getcovergroups(coverdefdir, coverfiles)
    formatstrlen = str(int(xlen/4))
    formatstr = "0x{:0" + formatstrlen + "x}" # format as xlen-bit hexadecimal number
    formatrefstr = "{:08x}" # format as xlen-bit hexadecimal number with no leading 0x
    if (xlen == 32):
      storecmd = "sw"
      wordsize = 4
    else:
      storecmd = "sd"
      wordsize = 8
    corners_32 = [0, 1, 2, 2**(xlen-1), 2**(xlen-1)+1, 2**(xlen-1)-1, 2**(xlen-1)-2, 2**xlen-1, 2**xlen-2, 
               0b10101010101010101010101010101010, 0b01010101010101010101010101010101, 0b01011011101111001000100001110111]
    corners_64 = [0, 1, 2, 2**(xlen-1), 2**(xlen-1)+1, 2**(xlen-1)-1, 2**(xlen-1)-2, 2**xlen-1, 2**xlen-2, 
              2**(xlen//2)-1, 2**(xlen//2)-2,2**(xlen//2),2**(xlen//2)+1, 0b1010101010101010101010101010101010101010101010101010101010101010,
               0b0101010101010101010101010101010101010101010101010101010101010101, 0b0101101110111100100010000111011101100011101011101000011011110111]
    corners_imm = [0, 1, 2, 1023, 1024, 2047, -2048, -2047, -2, -1]

    WALLY = os.environ.get('WALLY')
    pathname = WALLY+"/addins/cvw-arch-verif/tests/rv" + str(xlen) + "/I/"
    cmd = "mkdir -p " + pathname + " ; rm -f " + pathname + "/*" # make directory and remove old tests in dir
    os.system(cmd)
    for test in coverpoints.keys():
      basename = "WALLY-COV-" + test 
      fname = pathname + "/" + basename + ".S"

      # print custom header part
      f = open(fname, "w")
      line = "///////////////////////////////////////////\n"
      f.write(line)
      line="// "+fname+ "\n// " + author + "\n"
      f.write(line)
      line ="// Created " + str(datetime.now()) + "\n"
      f.write(line)

      # insert generic header
      h = open(WALLY+"/addins/cvw-arch-verif/templates/testgen_header.S", "r")
      for line in h:  
        f.write(line)

      # print directed and random test vectors
      # Coverage for R-type arithmetic instructions
      #if (test not in rtests):
      #  exit("Error: %s not implemented yet" % test)
      #else:
      #  write_rtype_arith_vectors(test, xlen)
      write_tests(coverpoints[test], test, xlen) 

      # print footer
      line = "\n.EQU NUMTESTS," + str(1) + "\n\n"
      f.write(line)
      h = open(WALLY+"/addins/cvw-arch-verif/templates/testgen_footer.S", "r")
      for line in h:  
        f.write(line)

      # Finish
      f.close()
