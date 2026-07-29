cmake_minimum_required(VERSION 3.20)

if(DEFINED NM_OUTPUT_FILE)
    if(NOT EXISTS "${NM_OUTPUT_FILE}")
        message(FATAL_ERROR "nm fixture does not exist: ${NM_OUTPUT_FILE}")
    endif()
    file(READ "${NM_OUTPUT_FILE}" nm_output)
else()
    if(NOT DEFINED PLUGIN_FILE OR NOT EXISTS "${PLUGIN_FILE}")
        message(FATAL_ERROR "PLUGIN_FILE must name the built Linux plugin")
    endif()
    if(NOT DEFINED NM_TOOL OR NM_TOOL STREQUAL "" OR NOT EXISTS "${NM_TOOL}")
        message(FATAL_ERROR "NM_TOOL must name nm or llvm-nm")
    endif()
    execute_process(
        COMMAND "${NM_TOOL}" --dynamic --undefined-only --format=posix "${PLUGIN_FILE}"
        RESULT_VARIABLE nm_result
        OUTPUT_VARIABLE nm_output
        ERROR_VARIABLE nm_error
    )
    if(NOT nm_result EQUAL 0)
        message(FATAL_ERROR "Unable to inspect ${PLUGIN_FILE} with ${NM_TOOL}: ${nm_error}")
    endif()
endif()

# Endstone's public C++ plugin API is resolved by libendstone_runtime at dlopen
# time. Bedrock's ABI and endstone::core implementation types are private, so
# every such reference must be implemented inside this exact-build plugin.
set(bedrock_symbol_pattern
    "^_Z(NK?|TV|TI|TS)([0-9]+(BaseGameVersion|Block|BlockActor|BlockSource|BlockType|ByteArrayTag|ByteTag|CompoundTag|Container|Dimension|DoubleTag|DynamicContainerManager|DynamicContainerTracker|EndTag|FloatTag|HashedString|IContainerRegistryAccess|IContainerRegistryTracker|Int64Tag|IntArrayTag|IntTag|Item|ItemDescriptor|ItemInstance|ItemRegistry|ItemRegistryManager|ItemStack|ItemStackBase|Inventory|Player|PlayerInventory|EnderChestContainer|IVanillaMainBlockActorComponent|LevelChunk|ListTag|ShortTag|StringTag|Tag|WeakPtr|WeakRef)|N?8endstone4core)"
)

string(REPLACE "\r\n" "\n" nm_output "${nm_output}")
string(REPLACE "\n" ";" nm_lines "${nm_output}")
set(undefined_bedrock_symbols)
foreach(line IN LISTS nm_lines)
    # POSIX nm format is: <symbol> <type> [value] [size]. Upper-case U is a
    # strong unresolved relocation; lower-case w/v weak imports may be absent.
    if(line MATCHES "^([^ ]+) U([ ]|$)")
        set(symbol "${CMAKE_MATCH_1}")
        if(symbol MATCHES "${bedrock_symbol_pattern}")
            list(APPEND undefined_bedrock_symbols "${symbol}")
        endif()
    endif()
endforeach()

if(undefined_bedrock_symbols)
    list(REMOVE_DUPLICATES undefined_bedrock_symbols)
    list(SORT undefined_bedrock_symbols)
    string(JOIN "\n  " formatted_symbols ${undefined_bedrock_symbols})
    message(FATAL_ERROR
        "Plugin contains private Bedrock or Endstone-core references that the runtime cannot export:\n"
        "  ${formatted_symbols}\n"
        "Link the exact Endstone Bedrock implementation; do not add untyped no-op stubs."
    )
endif()

if(DEFINED PLUGIN_FILE)
    message(STATUS "Verified that ${PLUGIN_FILE} has no unresolved Bedrock ABI symbols")
endif()
