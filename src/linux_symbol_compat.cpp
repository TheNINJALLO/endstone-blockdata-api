#if defined(__linux__) && !defined(_WIN32)
extern "C" {
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
