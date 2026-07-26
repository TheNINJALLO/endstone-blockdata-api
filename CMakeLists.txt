cmake_minimum_required(VERSION 3.20)
project(endstone_blockdata VERSION 0.4.5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(ENDSTONE_BLOCKDATA_RELEASE_VERSION "${PROJECT_VERSION}")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/SOURCE_RELEASE.json")
    file(READ "${CMAKE_CURRENT_SOURCE_DIR}/SOURCE_RELEASE.json" ENDSTONE_BLOCKDATA_RELEASE_JSON)
    string(JSON ENDSTONE_BLOCKDATA_RELEASE_VERSION
        GET "${ENDSTONE_BLOCKDATA_RELEASE_JSON}" version
    )
endif()
string(REPLACE "." "\\." ENDSTONE_BLOCKDATA_PROJECT_VERSION_REGEX "${PROJECT_VERSION}")
if(NOT ENDSTONE_BLOCKDATA_RELEASE_VERSION MATCHES "^${ENDSTONE_BLOCKDATA_PROJECT_VERSION_REGEX}($|[-+])")
    message(FATAL_ERROR
        "SOURCE_RELEASE.json version '${ENDSTONE_BLOCKDATA_RELEASE_VERSION}' does not match project version '${PROJECT_VERSION}'")
endif()

option(ENDSTONE_BLOCKDATA_BUILD_TESTS "Build portable tests" ON)
option(ENDSTONE_BLOCKDATA_BUILD_PLUGIN "Build the Endstone plugin wrapper" OFF)
option(ENDSTONE_BLOCKDATA_BUILD_PYTHON "Build portable pybind11 bindings" OFF)
option(ENDSTONE_BLOCKDATA_BUILD_LIVE_PYTHON "Build live Endstone Python bridge" ON)
option(ENDSTONE_BLOCKDATA_BUILD_NATIVE_2630 "Build exact BDS 26.30-family adapter" ON)
set(ENDSTONE_BDS_BUILD "1.26.33" CACHE STRING "Exact supported BDS build")
string(REPLACE "." "_" ENDSTONE_BDS_BUILD_FILE "${ENDSTONE_BDS_BUILD}")
if(DEFINED ENDSTONE_CONAN_BDS_BUILD AND
   NOT ENDSTONE_CONAN_BDS_BUILD STREQUAL ENDSTONE_BDS_BUILD)
    message(FATAL_ERROR
        "Conan dependencies target BDS ${ENDSTONE_CONAN_BDS_BUILD}, but CMake targets ${ENDSTONE_BDS_BUILD}"
    )
endif()

add_library(endstone_blockdata_core STATIC
    src/block_data_service.cpp
    src/in_memory_adapter.cpp
    src/nbt.cpp
    src/audit.cpp
    src/container_audit_reactor.cpp
    src/version_gate.cpp
)
target_include_directories(endstone_blockdata_core PUBLIC include)
target_compile_features(endstone_blockdata_core PUBLIC cxx_std_20)

configure_file(include/version.h.in ${CMAKE_CURRENT_BINARY_DIR}/include/version.h @ONLY)

if(ENDSTONE_BLOCKDATA_BUILD_PLUGIN)
    if(NOT DEFINED ENDSTONE_CONAN_BDS_BUILD)
        message(FATAL_ERROR
            "ENDSTONE_CONAN_BDS_BUILD is missing; configure the exact plugin with this project's Conan toolchain")
    endif()
    if(ENDSTONE_BDS_BUILD STREQUAL "1.26.33")
        set(ENDSTONE_EXACT_TAG "v0.11.6")
    else()
        message(FATAL_ERROR "The exact adapter supports only BDS 1.26.33 with Endstone v0.11.6")
    endif()
    string(REGEX REPLACE "^v" "" ENDSTONE_EXACT_VERSION "${ENDSTONE_EXACT_TAG}")

    # Private Bedrock headers use Endstone's complete dependency graph.
    # Conan generates these package configs from the exact versions pinned in conanfile.py.
    find_package(base64 REQUIRED)
    find_package(Boost REQUIRED)
    find_package(concurrentqueue REQUIRED)
    find_package(cpptrace REQUIRED)
    find_package(date REQUIRED)
    find_package(EnTT REQUIRED)
    find_package(expected-lite REQUIRED)
    find_package(funchook REQUIRED)
    find_package(glm REQUIRED)
    find_package(magic_enum REQUIRED)
    find_package(Microsoft.GSL REQUIRED)
    find_package(nlohmann_json REQUIRED)
    find_package(raknet REQUIRED)
    find_package(replxx REQUIRED)
    find_package(sentry REQUIRED)
    find_package(spdlog REQUIRED)
    find_package(tomlplusplus REQUIRED)
    find_package(zstr REQUIRED)

    include(FetchContent)
    FetchContent_Declare(endstone
        GIT_REPOSITORY https://github.com/EndstoneMC/endstone.git
        GIT_TAG ${ENDSTONE_EXACT_TAG}
    )
    FetchContent_MakeAvailable(endstone)

    if(EXISTS "${endstone_SOURCE_DIR}/include/endstone/identifier.h")
        file(READ "${endstone_SOURCE_DIR}/include/endstone/identifier.h" ENDSTONE_IDENTIFIER_H_CONTENT)
        string(REPLACE "-> format_context::iterator" "-> typename FormatContext::iterator" ENDSTONE_IDENTIFIER_H_CONTENT "${ENDSTONE_IDENTIFIER_H_CONTENT}")
        file(WRITE "${endstone_SOURCE_DIR}/include/endstone/identifier.h" "${ENDSTONE_IDENTIFIER_H_CONTENT}")
    endif()

    if(EXISTS "${endstone_SOURCE_DIR}/src/bedrock/server/commands/command_registry.h")
        file(READ "${endstone_SOURCE_DIR}/src/bedrock/server/commands/command_registry.h" ENDSTONE_CMD_REG_CONTENT)
        string(REPLACE "R\"(, \"children\": {})\", *it->child)" "R\"(, \"children\": {})\", 0)" ENDSTONE_CMD_REG_CONTENT "${ENDSTONE_CMD_REG_CONTENT}")
        file(WRITE "${endstone_SOURCE_DIR}/src/bedrock/server/commands/command_registry.h" "${ENDSTONE_CMD_REG_CONTENT}")
    endif()

    if(EXISTS "${endstone_SOURCE_DIR}/src/bedrock/platform/result.h")
        file(READ "${endstone_SOURCE_DIR}/src/bedrock/platform/result.h" ENDSTONE_RESULT_H_CONTENT)
        string(REPLACE "std::format(\"Error: {}\\nCall stack:{}\", error, call_stack)" "std::string(\"Error: \") + error" ENDSTONE_RESULT_H_CONTENT "${ENDSTONE_RESULT_H_CONTENT}")
        set(ENDSTONE_RESULT_ERROR_FORMAT "std::format(\"{}\", error_info.error)")
        set(ENDSTONE_RESULT_ERROR_MESSAGE "error_info.error.message()")
        string(FIND "${ENDSTONE_RESULT_H_CONTENT}" "${ENDSTONE_RESULT_ERROR_FORMAT}" ENDSTONE_RESULT_ERROR_FORMAT_INDEX)
        string(FIND "${ENDSTONE_RESULT_H_CONTENT}" "${ENDSTONE_RESULT_ERROR_MESSAGE}" ENDSTONE_RESULT_ERROR_MESSAGE_INDEX)
        if(ENDSTONE_RESULT_ERROR_FORMAT_INDEX EQUAL -1 AND ENDSTONE_RESULT_ERROR_MESSAGE_INDEX EQUAL -1)
            message(FATAL_ERROR "Endstone v0.11.6 result.h no longer contains the expected std::error_code format expression")
        endif()
        string(REPLACE "${ENDSTONE_RESULT_ERROR_FORMAT}" "${ENDSTONE_RESULT_ERROR_MESSAGE}" ENDSTONE_RESULT_H_CONTENT "${ENDSTONE_RESULT_H_CONTENT}")
        file(WRITE "${endstone_SOURCE_DIR}/src/bedrock/platform/result.h" "${ENDSTONE_RESULT_H_CONTENT}")
    endif()

    # The native adapter passes Bedrock-owned types across the ABI. Link the
    # exact Endstone tag's implementations instead of satisfying relocations
    # with untyped no-op weak symbols. Those shims made the library load only
    # until an NBT method returned an invalid value or iterator.
    if(NOT TARGET bedrock::bedrock)
        add_subdirectory(
            "${endstone_SOURCE_DIR}/src/bedrock"
            "${endstone_BINARY_DIR}/src/bedrock"
            EXCLUDE_FROM_ALL
        )
    endif()

    set(BLOCKDATA_PLUGIN_SOURCES
        src/plugin.cpp
        src/endstone_public_adapter.cpp
        src/native_runtime_bridge.cpp
    )
    if(ENDSTONE_BLOCKDATA_BUILD_NATIVE_2630)
        list(APPEND BLOCKDATA_PLUGIN_SOURCES
            src/bds_26_30_adapter.cpp
            src/native_item_bridge.cpp
        )
    endif()

    endstone_add_plugin(blockdata_api ${BLOCKDATA_PLUGIN_SOURCES})
    set_target_properties(blockdata_api PROPERTIES
        PREFIX ""
        OUTPUT_NAME "endstone_blockdata_bds_${ENDSTONE_BDS_BUILD_FILE}"
        BUILD_RPATH_USE_ORIGIN ON
        INSTALL_RPATH ""
        INSTALL_RPATH_USE_LINK_PATH FALSE
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN ON
    )
    target_include_directories(blockdata_api PRIVATE
        include
        ${CMAKE_CURRENT_BINARY_DIR}/include
        ${endstone_SOURCE_DIR}/src
        ${endstone_SOURCE_DIR}/include
        ${endstone_BINARY_DIR}/include
        ${endstone_BINARY_DIR}/include/generated
    )
    target_compile_definitions(blockdata_api PRIVATE
        ENDSTONE_BLOCKDATA_NATIVE_2630=$<BOOL:${ENDSTONE_BLOCKDATA_BUILD_NATIVE_2630}>
        ENDSTONE_BLOCKDATA_BDS_BUILD="${ENDSTONE_BDS_BUILD}"
        ENDSTONE_BLOCKDATA_ENDSTONE_VERSION="${ENDSTONE_EXACT_VERSION}"
        ENTT_SPARSE_PAGE=2048
        ENTT_NO_MIXIN=1
    )
    target_link_libraries(blockdata_api PRIVATE
        endstone_blockdata_core
        bedrock::bedrock
        aklomp::base64
        boost::boost
        concurrentqueue::concurrentqueue
        cpptrace::cpptrace
        date::date
        EnTT::EnTT
        nonstd::expected-lite
        funchook::funchook
        glm::glm
        magic_enum::magic_enum
        Microsoft.GSL::GSL
        nlohmann_json::nlohmann_json
        raknet::raknet
        replxx::replxx
        sentry::sentry
        spdlog::spdlog
        tomlplusplus::tomlplusplus
        zstr::zstr
        ${CMAKE_DL_LIBS}
    )
    if(UNIX)
        target_compile_options(blockdata_api PRIVATE -fms-extensions)
        # Bedrock is a private, exact-build ABI implementation. Do not export
        # or interpose its static-library symbols into Endstone's plugin scope.
        target_link_options(blockdata_api PRIVATE "LINKER:--exclude-libs,ALL")
        target_link_options(blockdata_api PRIVATE -Wl,--no-undefined)
    endif()

    if(UNIX AND NOT APPLE)
        add_custom_command(TARGET blockdata_api POST_BUILD
            COMMAND "${CMAKE_COMMAND}"
                "-DPLUGIN_FILE:FILEPATH=$<TARGET_FILE:blockdata_api>"
                "-DNM_TOOL:FILEPATH=${CMAKE_NM}"
                -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/verify_no_undefined_bedrock_symbols.cmake"
            COMMENT "Checking the plugin for unresolved Bedrock ABI symbols"
            VERBATIM
        )
    endif()

    install(TARGETS blockdata_api
        RUNTIME DESTINATION plugins COMPONENT blockdata_package
        LIBRARY DESTINATION plugins COMPONENT blockdata_package
        ARCHIVE DESTINATION lib COMPONENT blockdata_package
    )

    if(ENDSTONE_BLOCKDATA_BUILD_LIVE_PYTHON)
        FetchContent_Declare(pybind11_live
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v3.0.1
        )
        FetchContent_MakeAvailable(pybind11_live)
        pybind11_add_module(_endstone_blockdata_live MODULE src/live_python_bindings.cpp)
        set_target_properties(_endstone_blockdata_live PROPERTIES
            BUILD_RPATH_USE_ORIGIN ON
            INSTALL_RPATH ""
            INSTALL_RPATH_USE_LINK_PATH FALSE
            CXX_VISIBILITY_PRESET hidden
            VISIBILITY_INLINES_HIDDEN ON
        )
        target_link_libraries(_endstone_blockdata_live PRIVATE
            endstone::endstone
            endstone_blockdata_core
        )
        target_include_directories(_endstone_blockdata_live PRIVATE
            include
            ${CMAKE_CURRENT_BINARY_DIR}/include
            ${endstone_SOURCE_DIR}/include
            ${endstone_SOURCE_DIR}/src
            ${endstone_BINARY_DIR}/include
            ${endstone_BINARY_DIR}/include/generated
        )
        if(UNIX)
            target_compile_options(_endstone_blockdata_live PRIVATE -fms-extensions)
            target_link_options(_endstone_blockdata_live PRIVATE "LINKER:--exclude-libs,ALL")
            # Match endstone_add_plugin's self-contained Linux runtime linkage;
            # the bridge is loaded by Python as its own shared object.
            if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
                target_compile_options(_endstone_blockdata_live PRIVATE -stdlib=libc++)
                target_link_options(_endstone_blockdata_live PRIVATE -stdlib=libc++)
                target_link_libraries(_endstone_blockdata_live PRIVATE
                    -static-libgcc
                    -static-libstdc++
                    libc++.a
                    libc++abi.a
                )
            endif()
        endif()
        add_dependencies(blockdata_api _endstone_blockdata_live)
        install(TARGETS _endstone_blockdata_live
            RUNTIME DESTINATION python COMPONENT blockdata_package
            LIBRARY DESTINATION python COMPONENT blockdata_package
        )
        if(UNIX AND NOT APPLE)
            add_custom_command(TARGET _endstone_blockdata_live POST_BUILD
                COMMAND "${CMAKE_COMMAND}"
                    "-DPLUGIN_FILE:FILEPATH=$<TARGET_FILE:_endstone_blockdata_live>"
                    "-DNM_TOOL:FILEPATH=${CMAKE_NM}"
                    -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/verify_no_undefined_bedrock_symbols.cmake"
                COMMENT "Checking the live Python bridge for unresolved Bedrock ABI symbols"
                VERBATIM
            )
        endif()
    endif()

    install(DIRECTORY python/endstone_blockdata DESTINATION python COMPONENT blockdata_package)
    install(DIRECTORY include/endstone_blockdata DESTINATION include COMPONENT blockdata_package)
    install(FILES
        README.md
        LICENSE
        BUILD_STATUS.md
        VALIDATION_RESULTS.md
        docs/INSTALL.md
        docs/CI_TROUBLESHOOTING.md
        docs/BDS_26_30_ADAPTER.md
        DESTINATION .
        COMPONENT blockdata_package
    )
    install(FILES compatibility/versions.json DESTINATION compatibility COMPONENT blockdata_package)
endif()

if(ENDSTONE_BLOCKDATA_BUILD_PYTHON)
    include(FetchContent)
    FetchContent_Declare(pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v3.0.1
    )
    FetchContent_MakeAvailable(pybind11)
    pybind11_add_module(_endstone_blockdata src/python_bindings.cpp)
    target_link_libraries(_endstone_blockdata PRIVATE endstone_blockdata_core)
    target_include_directories(_endstone_blockdata PRIVATE include)
endif()

if(ENDSTONE_BLOCKDATA_BUILD_TESTS)
    enable_testing()
    add_executable(blockdata_tests tests/cpp/test_blockdata.cpp)
    target_link_libraries(blockdata_tests PRIVATE endstone_blockdata_core)
    if(MSVC)
        target_compile_options(blockdata_tests PRIVATE /UNDEBUG)
    else()
        target_compile_options(blockdata_tests PRIVATE -UNDEBUG)
    endif()
    add_test(NAME blockdata_tests COMMAND blockdata_tests)

    add_test(
        NAME blockdata_symbol_gate_accepts_clean_elf
        COMMAND "${CMAKE_COMMAND}"
            "-DNM_OUTPUT_FILE:FILEPATH=${CMAKE_CURRENT_SOURCE_DIR}/tests/cmake/nm_clean.txt"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/verify_no_undefined_bedrock_symbols.cmake"
    )
    add_test(
        NAME blockdata_symbol_gate_rejects_undefined_bedrock
        COMMAND "${CMAKE_COMMAND}"
            "-DNM_OUTPUT_FILE:FILEPATH=${CMAKE_CURRENT_SOURCE_DIR}/tests/cmake/nm_undefined_bedrock.txt"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/verify_no_undefined_bedrock_symbols.cmake"
    )
    set_tests_properties(blockdata_symbol_gate_rejects_undefined_bedrock PROPERTIES WILL_FAIL TRUE)
endif()
