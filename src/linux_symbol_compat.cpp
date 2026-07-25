#if defined(__linux__) && !defined(_WIN32)
extern "C" {
    // Weak object stubs for Bedrock item stack static constants
    __attribute__((weak)) char _ZN9ItemStack10EMPTY_ITEME[256] = {0};
    __attribute__((weak)) char _ZN13ItemStackBase10EMPTY_ITEME[256] = {0};

    // Weak object stubs for Bedrock Item/Block vtables & typeinfo
    __attribute__((weak)) void *_ZTV9ItemStack[32] = {0};
    __attribute__((weak)) void *_ZTV13ItemStackBase[32] = {0};
    __attribute__((weak)) void *_ZTV12ItemInstance[32] = {0};
    __attribute__((weak)) void *_ZTV4Item[32] = {0};
    __attribute__((weak)) void *_ZTV5Block[32] = {0};
    __attribute__((weak)) void *_ZTV11BlockLegacy[32] = {0};
    __attribute__((weak)) void *_ZTV9BlockActor[32] = {0};
    __attribute__((weak)) void *_ZTV10BlockSource[32] = {0};

    __attribute__((weak)) void *_ZTI9ItemStack[8] = {0};
    __attribute__((weak)) void *_ZTI13ItemStackBase[8] = {0};
    __attribute__((weak)) void *_ZTI12ItemInstance[8] = {0};
    __attribute__((weak)) void *_ZTI4Item[8] = {0};
    __attribute__((weak)) void *_ZTI5Block[8] = {0};
    __attribute__((weak)) void *_ZTI11BlockLegacy[8] = {0};
    __attribute__((weak)) void *_ZTI9BlockActor[8] = {0};
    __attribute__((weak)) void *_ZTI10BlockSource[8] = {0};

    // Weak object stubs for Bedrock Tag vtables & typeinfo
    __attribute__((weak)) void *_ZTV7ListTag[32] = {0};
    __attribute__((weak)) void *_ZTV11CompoundTag[32] = {0};
    __attribute__((weak)) void *_ZTV10CompoundTag[32] = {0};
    __attribute__((weak)) void *_ZTV9DoubleTag[32] = {0};
    __attribute__((weak)) void *_ZTV8FloatTag[32] = {0};
    __attribute__((weak)) void *_ZTV6IntTag[32] = {0};
    __attribute__((weak)) void *_ZTV8Int64Tag[32] = {0};
    __attribute__((weak)) void *_ZTV8ShortTag[32] = {0};
    __attribute__((weak)) void *_ZTV7ByteTag[32] = {0};
    __attribute__((weak)) void *_ZTV12ByteArrayTag[32] = {0};
    __attribute__((weak)) void *_ZTV11IntArrayTag[32] = {0};
    __attribute__((weak)) void *_ZTV6EndTag[32] = {0};
    __attribute__((weak)) void *_ZTV9StringTag[32] = {0};
    __attribute__((weak)) void *_ZTV3Tag[32] = {0};

    __attribute__((weak)) void *_ZTI7ListTag[8] = {0};
    __attribute__((weak)) void *_ZTI11CompoundTag[8] = {0};
    __attribute__((weak)) void *_ZTI10CompoundTag[8] = {0};
    __attribute__((weak)) void *_ZTI9DoubleTag[8] = {0};
    __attribute__((weak)) void *_ZTI8FloatTag[8] = {0};
    __attribute__((weak)) void *_ZTI6IntTag[8] = {0};
    __attribute__((weak)) void *_ZTI8Int64Tag[8] = {0};
    __attribute__((weak)) void *_ZTI8ShortTag[8] = {0};
    __attribute__((weak)) void *_ZTI7ByteTag[8] = {0};
    __attribute__((weak)) void *_ZTI12ByteArrayTag[8] = {0};
    __attribute__((weak)) void *_ZTI11IntArrayTag[8] = {0};
    __attribute__((weak)) void *_ZTI6EndTag[8] = {0};
    __attribute__((weak)) void *_ZTI9StringTag[8] = {0};
    __attribute__((weak)) void *_ZTI3Tag[8] = {0};
    __attribute__((weak)) void *_ZTIN8endstone4core17EndstoneDimensionE[8] = {0};

    // CompoundTag method weak stubs (both libc++ std::__1 and libstdc++ std::__cxx11)
    __attribute__((weak)) void _ZN11CompoundTag9putStringENSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEES6_() {}
    __attribute__((weak)) void _ZN11CompoundTag9putStringENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEES5_() {}
    __attribute__((weak)) void _ZN11CompoundTag6putIntENSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEi() {}
    __attribute__((weak)) void _ZN11CompoundTag6putIntENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEi() {}
    __attribute__((weak)) void _ZN11CompoundTag7putByteENSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEh() {}
    __attribute__((weak)) void _ZN11CompoundTag7putByteENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEEh() {}
    __attribute__((weak)) void _ZN11CompoundTag8putShortENSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEs() {}
    __attribute__((weak)) void _ZN11CompoundTag8putShortENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEEs() {}
    __attribute__((weak)) void _ZN11CompoundTag9putInt64ENSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEl() {}
    __attribute__((weak)) void _ZN11CompoundTag9putInt64ENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEEl() {}
    __attribute__((weak)) void _ZN11CompoundTag8putFloatENSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEf() {}
    __attribute__((weak)) void _ZN11CompoundTag8putFloatENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEEf() {}
    __attribute__((weak)) void _ZN11CompoundTag9putDoubleENSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEd() {}
    __attribute__((weak)) void _ZN11CompoundTag9putDoubleENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEEd() {}
    __attribute__((weak)) void _ZN11CompoundTag10putBooleanENSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEb() {}
    __attribute__((weak)) void _ZN11CompoundTag10putBooleanENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEEb() {}

    // Weak function stubs for missing BDS/Endstone internal functions
    __attribute__((weak)) void _ZN12HashedStringC1EPKc() {}
    __attribute__((weak)) void _ZN12HashedStringC2EPKc() {}
    __attribute__((weak)) void _ZN12HashedStringC1ERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE() {}
    __attribute__((weak)) void _ZN12HashedStringC2ERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE() {}
    __attribute__((weak)) void _ZN12HashedStringC1EDn() {}
    __attribute__((weak)) void _ZN12HashedStringC2EDn() {}

    __attribute__((weak)) void _ZNK3Tag5printER11PrintStream() {}
    __attribute__((weak)) void _ZNK3Tag5printERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEER11PrintStream() {}
    __attribute__((weak)) void _ZN15BaseGameVersionC1Ev() {}
    __attribute__((weak)) void _ZN15BaseGameVersionC2Ev() {}
    __attribute__((weak)) void _ZN15BaseGameVersionC1Eb() {}
    __attribute__((weak)) void _ZN15BaseGameVersionC2Eb() {}
    __attribute__((weak)) void _ZNK8endstone4core17EndstoneDimension9getHandleEv() {}
}
#endif
