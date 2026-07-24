cmake_minimum_required(VERSION 3.20)
project(endstone_blockdata VERSION 0.4.5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(ENDSTONE_BLOCKDATA_BUILD_TESTS "Build portable tests" ON)
option(ENDSTONE_BLOCKDATA_BUILD_PLUGIN "Build the Endstone plugin wrapper" OFF)
option(ENDSTONE_BLOCKDATA_BUILD_PYTHON "Build portable pybind11 bindings" OFF)
option(ENDSTONE_BLOCKDATA_BUILD_LIVE_PYTHON "Build live Endstone Python bridge" ON)
option(ENDSTONE_BLOCKDATA_BUILD_NATIVE_2630 "Build exact BDS 26.30-family adapter" ON)
set(ENDSTONE_BDS_BUILD "1.26.33" CACHE STRING "Exact BDS build: 1.26.32 or 1.26.33")
string(REPLACE "." "_" ENDSTONE_BDS_BUILD_FILE "${ENDSTONE_BDS_BUILD}")

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
    if(ENDSTONE_BDS_BUILD STREQUAL "1.26.32")
        set(ENDSTONE_EXACT_TAG "v0.11.5")
    elseif(ENDSTONE_BDS_BUILD STREQUAL "1.26.33")
        set(ENDSTONE_EXACT_TAG "v0.11.6")
    elseif(ENDSTONE_BLOCKDATA_BUILD_NATIVE_2630)
        message(FATAL_ERROR "Native 26.30 adapter supports only BDS 1.26.32 and 1.26.33")
    else()
        set(ENDSTONE_EXACT_TAG "v0.11.6")
    endif()

    # Private Bedrock headers use Endstone's complete dependency graph.
    # Conan generates these package configs from the exact versions pinned in conanfile.py.
    find_package(base64 REQUIRED)
    find_package(Boost REQUIRED)
    find_package(concurrentqueue REQUIRED)
    find_package(cpptrace REQUIRED)
    find_package(date REQUIRED)
    find_package(EnTT REQUIRED)
    find_package(expected-lite REQUIRED)
    find_package(fmt REQUIRED)
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


    set(BLOCKDATA_PLUGIN_SOURCES src/plugin.cpp src/endstone_public_adapter.cpp)
    if(ENDSTONE_BLOCKDATA_BUILD_NATIVE_2630)
        list(APPEND BLOCKDATA_PLUGIN_SOURCES src/bds_26_30_adapter.cpp)
    endif()

    endstone_add_plugin(blockdata_api ${BLOCKDATA_PLUGIN_SOURCES})
    set_target_properties(blockdata_api PROPERTIES
        PREFIX ""
        OUTPUT_NAME "endstone_blockdata_bds_${ENDSTONE_BDS_BUILD_FILE}"
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
        ENTT_SPARSE_PAGE=2048
        ENTT_NO_MIXIN=1
    )
    target_link_libraries(blockdata_api PRIVATE
        endstone_blockdata_core
        aklomp::base64
        boost::boost
        concurrentqueue::concurrentqueue
        cpptrace::cpptrace
        date::date
        EnTT::EnTT
        nonstd::expected-lite
        fmt::fmt
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
    )
    if(UNIX)
        target_compile_options(blockdata_api PRIVATE -fms-extensions)
    endif()

    install(TARGETS blockdata_api
        RUNTIME DESTINATION plugins
        LIBRARY DESTINATION plugins
        ARCHIVE DESTINATION lib
        COMPONENT blockdata_package
    )
    install(FILES $<TARGET_FILE:blockdata_api> DESTINATION plugins COMPONENT blockdata_package)

    if(ENDSTONE_BLOCKDATA_BUILD_LIVE_PYTHON)
        FetchContent_Declare(pybind11_live
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v3.0.1
        )
        FetchContent_MakeAvailable(pybind11_live)
        pybind11_add_module(_endstone_blockdata_live MODULE src/live_python_bindings.cpp)
        target_link_libraries(_endstone_blockdata_live PRIVATE
            endstone_blockdata_core
            aklomp::base64
            boost::boost
            concurrentqueue::concurrentqueue
            cpptrace::cpptrace
            date::date
            EnTT::EnTT
            nonstd::expected-lite
            fmt::fmt
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
        )
        target_include_directories(_endstone_blockdata_live PRIVATE
            include
            ${CMAKE_CURRENT_BINARY_DIR}/include
            ${endstone_SOURCE_DIR}/include
            ${endstone_SOURCE_DIR}/src
            ${endstone_BINARY_DIR}/include
            ${endstone_BINARY_DIR}/include/generated
        )
        install(TARGETS _endstone_blockdata_live
            RUNTIME DESTINATION python
            LIBRARY DESTINATION python
            COMPONENT blockdata_package
        )
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
    add_test(NAME blockdata_tests COMMAND blockdata_tests)
endif()
