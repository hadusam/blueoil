package bxb.a2f

import chisel3._
import chisel3.util._

import bxb.util.{Util}

class A2fSequencer(addrWidth: Int) extends Module {
  val io = IO(new Bundle {
    val kernelVCount = Input(UInt(2.W))
    val kernelHCount = Input(UInt(2.W))
    val tileVCount = Input(UInt(addrWidth.W))
    val tileHCount = Input(UInt(addrWidth.W))
    val tileStep = Input(UInt(2.W))
    val tileGap = Input(UInt(2.W))
    val tileOffset = Input(UInt(addrWidth.W))
    val tileOffsetValid = Input(Bool())
    val control = Output(A2fControl(addrWidth, addrWidth))
    val controlValid = Output(Bool())
    // A Semaphore Pair Dec interface
    val aRawDec = Output(Bool())
    val aRawZero = Input(Bool())
    // M Semaphore Pair Dec interface
    val mRawDec = Output(Bool())
    val mRawZero = Input(Bool())
    // F Semaphore Pair Dec interface
    val fWarDec = Output(Bool())
    val fWarZero = Input(Bool())
  })

  object State {
    val idle :: doingFirst :: doingRest :: Nil = Enum(3)
  }

  val state = RegInit(State.idle)
  val idle = (state === State.idle)
  val doingFirst = (state === State.doingFirst)

  val controlWrite = RegInit(false.B)
  val controlAccumulate = RegInit(false.B)
  val controlEvenOdd = RegInit(0.U)

  // asserted at the last element of last 1x1 convolution
  val syncIncAWar = Wire(Bool())
  // asserted at the first element of first 1x1 convolution
  val syncDecARaw = RegInit(false.B)
  // asserted at the last element of 1x1 convolution
  val syncIncMWar = Wire(Bool())
  // asserted at the first element of 1x1 convolution
  val syncDecMRaw = RegInit(false.B)
  // asserted at the last element of last 1x1 convolution
  val syncIncFRaw = Wire(Bool())
  // asserted at the first element of first 1x1 convolution
  val syncDecFWar = RegInit(false.B)

  val waitRequired = ((syncDecARaw & io.aRawZero) | (syncDecMRaw & io.mRawZero) | (syncDecFWar & io.fWarZero))

  val tileHCountLeft = Reg(UInt(addrWidth.W))
  // the idea is to make combinational chains shorter
  // by feeding comparator output into delay registers
  // it will delay signal by one cycle thus last signal
  // should be generated one cycle earlier
  val tileHCountLast = RegNext(tileHCountLeft === 2.U)
  when(~waitRequired) {
    when(idle | tileHCountLast) {
      tileHCountLeft := io.tileHCount
    }.otherwise {
      tileHCountLeft := tileHCountLeft - 1.U
    }
  }

  val tileVCountLeft = Reg(UInt(addrWidth.W))
  val tileVCountLast = RegNext(tileVCountLeft === 1.U) & tileHCountLast
  when(~waitRequired) {
    when(idle | tileVCountLast) {
      tileVCountLeft := io.tileVCount
    }.elsewhen(tileHCountLast) {
      tileVCountLeft := tileVCountLeft - 1.U
    }
  }

  val kernelHCountLeft = Reg(UInt(2.W))
  val kernelHCountLast = RegNext(kernelHCountLeft === 1.U) & tileVCountLast
  when(~waitRequired) {
    when(idle | kernelHCountLast) {
      kernelHCountLeft := io.kernelHCount
    }.elsewhen(tileVCountLast) {
      kernelHCountLeft := kernelHCountLeft - 1.U
    }
  }

  val kernelVCountLeft = Reg(UInt(2.W))
  val kernelVCountLast = RegNext(kernelVCountLeft === 1.U) & kernelHCountLast
  when(~waitRequired) {
    when(idle | kernelVCountLast) {
      kernelVCountLeft := io.kernelVCount
    }.elsewhen(kernelHCountLast) {
      kernelVCountLeft := kernelVCountLeft - 1.U
    }
  }

  val offset = Reg(UInt(addrWidth.W))
  when(~waitRequired) {
    when(idle | kernelVCountLast) {
      offset := io.tileOffset
    }.elsewhen(kernelHCountLast) {
      offset := offset + io.tileHCount
    }.elsewhen(tileVCountLast) {
      offset := offset + 1.U
    }
  }

  val aAddr = Reg(UInt(addrWidth.W))
  when(~waitRequired) {
    when(idle | kernelVCountLast) {
      aAddr := io.tileOffset
    }.elsewhen(kernelHCountLast) {
      aAddr := offset + io.tileHCount
    }.elsewhen(tileVCountLast) {
      aAddr := offset + 1.U
    }.elsewhen(tileHCountLast) {
      aAddr := aAddr + io.tileGap
    }.otherwise {
      aAddr := aAddr + io.tileStep
    }
  }

  val fAddr = Reg(UInt(addrWidth.W))
  when(~waitRequired) {
    when(idle | tileVCountLast) {
      fAddr := io.tileOffset
    }.otherwise {
      fAddr := fAddr + 1.U
    }
  }

  io.control.aAddr := aAddr
  io.control.fAddr := fAddr

  when(~waitRequired) {
    when(tileVCountLast) {
      controlEvenOdd := ~controlEvenOdd
    }
    when(idle | kernelVCountLast) {
      controlAccumulate := false.B
      when(io.tileOffsetValid) {
        state := State.doingFirst
        controlWrite := true.B
      }.otherwise {
        state := State.idle
        controlWrite := false.B
      }
    }.elsewhen(doingFirst & tileVCountLast) {
      controlAccumulate := true.B
      state := State.doingRest
    }
  }

  io.control.writeEnable := ~waitRequired & controlWrite
  io.control.accumulate := controlAccumulate
  io.control.evenOdd := controlEvenOdd
  io.controlValid := controlWrite

  when(~waitRequired) {
    when(idle) {
      syncDecARaw := io.tileOffsetValid
    }.elsewhen(kernelVCountLast) {
      syncDecARaw := true.B
    }.otherwise {
      syncDecARaw := false.B
    }
  }
  syncIncAWar := kernelVCountLast

  when(~waitRequired) {
    when(idle) {
      syncDecMRaw := io.tileOffsetValid
    }.elsewhen(tileVCountLast) {
      syncDecMRaw := true.B
    }.otherwise {
      syncDecMRaw := false.B
    }
  }
  syncIncMWar := tileVCountLast

  when(~waitRequired) {
    when(idle) {
      syncDecFWar := io.tileOffsetValid
    }.elsewhen(kernelVCountLast) {
      syncDecFWar := true.B
    }.otherwise {
      syncDecFWar := false.B
    }
  }
  syncIncFRaw := kernelVCountLast

  io.aRawDec := ~waitRequired & syncDecARaw
  io.mRawDec := ~waitRequired & syncDecMRaw
  io.fWarDec := ~waitRequired & syncDecFWar
  io.control.syncInc.aWar := ~waitRequired & syncIncAWar
  io.control.syncInc.mWar := ~waitRequired & syncIncMWar
  io.control.syncInc.fRaw := ~waitRequired & syncIncFRaw
}

object A2fSequencer {
  def main(args: Array[String]): Unit = {
    println(Util.getVerilog(new A2fSequencer(10)))
  }
}
