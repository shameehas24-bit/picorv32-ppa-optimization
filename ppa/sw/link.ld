MEMORY { ram (rwx) : ORIGIN = 0x00000000, LENGTH = 64K }
SECTIONS {
  .text : { *(.text.init) *(.text*) } > ram
  .rodata : { *(.rodata*) } > ram
  .data : { *(.data*) *(.sdata*) } > ram
  .bss : { *(.bss*) *(.sbss*) *(COMMON) } > ram
  _stack_top = ORIGIN(ram) + LENGTH(ram);
}
