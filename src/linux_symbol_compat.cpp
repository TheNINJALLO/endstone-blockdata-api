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

    // ItemStack and ItemStackBase method weak stubs
    __attribute__((weak)) void _ZN13ItemStackBaseC1Ev() {}
    __attribute__((weak)) void _ZN13ItemStackBaseC2Ev() {}
    __attribute__((weak)) void _ZN13ItemStackBaseC1ERKS_() {}
    __attribute__((weak)) void _ZN13ItemStackBaseC2ERKS_() {}
    __attribute__((weak)) void _ZN13ItemStackBaseaSERKS_() {}
    __attribute__((weak)) void _ZNK13ItemStackBase6isNullEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase13getDescriptorEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase11matchesItemERKS_() {}
    __attribute__((weak)) void _ZN13ItemStackBase3setEi() {}
    __attribute__((weak)) void _ZNK13ItemStackBase6hasTagERK14VanillaItemTag() {}
    __attribute__((weak)) void _ZNK13ItemStackBase11hasUserDataEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase15hasSameUserDataERKS_() {}
    __attribute__((weak)) void _ZN13ItemStackBase11setUserDataENSt3__110unique_ptrI11CompoundTagNS0_14default_deleteIS2_EEEE() {}
    __attribute__((weak)) void _ZN13ItemStackBase11setUserDataESt10unique_ptrI11CompoundTagSt14default_deleteIS1_EE() {}
    __attribute__((weak)) void _ZNK13ItemStackBase11getUserDataEv() {}
    __attribute__((weak)) void _ZN13ItemStackBase11getUserDataEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase7getItemEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase10getItemPtrEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase8getBlockEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase5getIdEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase8getIdAuxEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase7isBlockEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase29isValid_DeprecatedSeeCommentEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase15getMaxStackSizeEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase14getDamageValueEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase14hasDamageValueEv() {}
    __attribute__((weak)) void _ZN13ItemStackBase17removeDamageValueEv() {}
    __attribute__((weak)) void _ZN13ItemStackBase14setDamageValueEs() {}
    __attribute__((weak)) void _ZNK13ItemStackBase11getAuxValueEv() {}
    __attribute__((weak)) void _ZN13ItemStackBase11setAuxValueEs() {}
    __attribute__((weak)) void _ZNK13ItemStackBase7getNameEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase14getDescriptionIdEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase13getCustomNameEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase18hasCustomHoverNameEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase8getCountEv() {}
    __attribute__((weak)) void _ZNK13ItemStackBase10canPlaceOnEPK5Block() {}
    __attribute__((weak)) void _ZNK13ItemStackBase10canDestroyEPK5Block() {}
    __attribute__((weak)) void _ZN13ItemStackBase14setWasPickedUpEb() {}
    __attribute__((weak)) void _ZNK13ItemStackBase14getWasPickedUpEv() {}

    __attribute__((weak)) void _ZN9ItemStackC1Ev() {}
    __attribute__((weak)) void _ZN9ItemStackC2Ev() {}
    __attribute__((weak)) void _ZN9ItemStackC1ERKS_() {}
    __attribute__((weak)) void _ZN9ItemStackC2ERKS_() {}
    __attribute__((weak)) void _ZN9ItemStackaSERKS_() {}
    __attribute__((weak)) void _ZNK9ItemStack7isBundleEv() {}
    __attribute__((weak)) void _ZNK9ItemStack23getItemStackNetIdVariantEv() {}

    __attribute__((weak)) void _ZN12ItemInstanceC1Ev() {}
    __attribute__((weak)) void _ZN12ItemInstanceC2Ev() {}
    __attribute__((weak)) void _ZN12ItemInstanceC1ERKS_() {}
    __attribute__((weak)) void _ZN12ItemInstanceC2ERKS_() {}
    __attribute__((weak)) void _ZN12ItemInstanceaSERKS_() {}

    // Block method weak stubs
    __attribute__((weak)) void _ZNK5Block11hasPropertyE13BlockProperty() {}
    __attribute__((weak)) void _ZNK5Block16getLightEmissionEv() {}
    __attribute__((weak)) void _ZNK5Block16getTranslucencyEv() {}
    __attribute__((weak)) void _ZNK5Block7isSolidEv() {}
    __attribute__((weak)) void _ZNK5Block8getLightEv() {}
    __attribute__((weak)) void _ZNK5Block12getFlameOddsEv() {}
    __attribute__((weak)) void _ZNK5Block11getBurnOddsEv() {}
    __attribute__((weak)) void _ZNK5Block23getExplosionResistanceEv() {}
    __attribute__((weak)) void _ZNK5Block8hasStateERK10BlockState() {}
    __attribute__((weak)) void _ZNK5Block8hasStateERK12HashedString() {}
    __attribute__((weak)) void _ZNK5Block15isLavaBlockingEv() {}
    __attribute__((weak)) void _ZNK5Block27requiresCorrectToolForDropsEv() {}
    __attribute__((weak)) void _ZNK5Block12getThicknessEv() {}
    __attribute__((weak)) void _ZNK5Block11getMaterialEv() {}
    __attribute__((weak)) void _ZNK5Block11getFrictionEv() {}
    __attribute__((weak)) void _ZNK5Block15getDestroySpeedEv() {}
    __attribute__((weak)) void _ZNK5Block7getNameEv() {}
    __attribute__((weak)) void _ZNK5Block18getSerializationIdEv() {}
    __attribute__((weak)) void _ZNK5Block12getRuntimeIdEv() {}
    __attribute__((weak)) void _ZNK5Block13toDebugStringEv() {}
    __attribute__((weak)) void _ZNK5Block12getBlockTypeEv() {}
    __attribute__((weak)) void _ZNK5Block7getTagsEv() {}
    __attribute__((weak)) void _ZNK5Block13getDirectDataEv() {}

    // BlockType method weak stubs
    __attribute__((weak)) void _ZNK9BlockType6hasTagERK12HashedString() {}
    __attribute__((weak)) void _ZNK9BlockType6hasTagERKm() {}
    __attribute__((weak)) void _ZNK9BlockType11hasPropertyE13BlockProperty() {}
    __attribute__((weak)) void _ZNK9BlockType25tryGetStateFromLegacyDataEh() {}
    __attribute__((weak)) void _ZNK9BlockType8hasStateERK10BlockState() {}
    __attribute__((weak)) void _ZNK9BlockType8hasStateERK12HashedString() {}
    __attribute__((weak)) void _ZNK9BlockType27requiresCorrectToolForDropsEv() {}
    __attribute__((weak)) void _ZNK9BlockType7isSolidEv() {}
    __attribute__((weak)) void _ZNK9BlockType12getThicknessEv() {}
    __attribute__((weak)) void _ZNK9BlockType16getTranslucencyEv() {}
    __attribute__((weak)) void _ZNK9BlockType7getTagsEv() {}
    __attribute__((weak)) void _ZNK9BlockType11getMaterialEv() {}
    __attribute__((weak)) void _ZNK9BlockType16getDescriptionIdEv() {}
    __attribute__((weak)) void _ZNK9BlockType12getRawNameIdEv() {}
    __attribute__((weak)) void _ZNK9BlockType12getNamespaceEv() {}
    __attribute__((weak)) void _ZNK9BlockType7getNameEv() {}
    __attribute__((weak)) void _ZNK9BlockType15getDefaultStateEv() {}
    __attribute__((weak)) void _ZNK9BlockType26getRequiredBaseGameVersionEv() {}
    __attribute__((weak)) void _ZNK9BlockType15getBlockItemIdEv() {}
    __attribute__((weak)) void _ZNK9BlockType13getTintMethodEv() {}

    // BlockSource method weak stubs
    __attribute__((weak)) void _ZNK11BlockSource12isEmptyBlockERK8BlockPos() {}
    __attribute__((weak)) void _ZNK11BlockSource8getBiomeERK8BlockPos() {}

    // ListTag method weak stubs
    __attribute__((weak)) void _ZNK7ListTag3getEi() {}
    __attribute__((weak)) void _ZN7ListTag3getEi() {}
    __attribute__((weak)) void _ZN7ListTag3addESt10unique_ptrI3TagSt14default_deleteIS1_EE() {}
    __attribute__((weak)) void _ZNK7ListTag4sizeEv() {}
    __attribute__((weak)) void _ZN7ListTag14deleteChildrenEv() {}
    __attribute__((weak)) void _ZNK7ListTag9getStringEi() {}
    __attribute__((weak)) void _ZNK7ListTag11getCompoundEi() {}
    __attribute__((weak)) void _ZNK7ListTag6getIntEi() {}
    __attribute__((weak)) void _ZNK7ListTag8getFloatEi() {}
    __attribute__((weak)) void _ZNK7ListTag9getDoubleEi() {}
    __attribute__((weak)) void _ZNK7ListTag7getByteEi() {}
    __attribute__((weak)) void _ZNK7ListTag8getShortEi() {}
    __attribute__((weak)) void _ZNK7ListTag9getInt64Ei() {}

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

    __attribute__((weak)) void _ZNK11CompoundTag3getESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZN11CompoundTag3getESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag9getStringESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag11getCompoundESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZN11CompoundTag11getCompoundESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag7getListESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZN11CompoundTag7getListESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag6getIntESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag7getByteESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag8getShortESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag9getInt64ESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag8getFloatESt17basic_string_viewIcSt11char_traitsIcEE() {}
    __attribute__((weak)) void _ZNK11CompoundTag9getDoubleESt17basic_string_viewIcSt11char_traitsIcEE() {}

    // Tag base class method weak stubs
    __attribute__((weak)) void _ZNK3Tag6equalsERKS_() {}
    __attribute__((weak)) void _ZNK3Tag4copyEv() {}
    __attribute__((weak)) void _ZNK3Tag5getIdEv() {}
    __attribute__((weak)) void _ZNK3Tag8toStringEv() {}

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
