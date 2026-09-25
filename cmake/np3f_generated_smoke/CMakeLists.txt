cmake_minimum_required(VERSION 3.20)

project(AeroStadium2NP3FGeneratedSmoke LANGUAGES C CXX)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT DEFINED NP3F_GENERATED_DIR)
    message(FATAL_ERROR "NP3F_GENERATED_DIR was not provided.")
endif()

if(NOT DEFINED N64RECOMP_INCLUDE_DIR)
    message(FATAL_ERROR "N64RECOMP_INCLUDE_DIR was not provided.")
endif()

file(TO_CMAKE_PATH "${NP3F_GENERATED_DIR}" NP3F_GENERATED_DIR)
file(TO_CMAKE_PATH "${N64RECOMP_INCLUDE_DIR}" N64RECOMP_INCLUDE_DIR)

if(NOT EXISTS "${NP3F_GENERATED_DIR}/funcs.h")
    message(FATAL_ERROR "Missing generated funcs.h: ${NP3F_GENERATED_DIR}/funcs.h")
endif()

if(NOT EXISTS "${NP3F_GENERATED_DIR}/lookup.cpp")
    message(FATAL_ERROR "Missing generated lookup.cpp: ${NP3F_GENERATED_DIR}/lookup.cpp")
endif()

if(NOT EXISTS "${N64RECOMP_INCLUDE_DIR}/recomp.h")
    message(FATAL_ERROR "Missing N64Recomp recomp.h: ${N64RECOMP_INCLUDE_DIR}/recomp.h")
endif()

file(GLOB RECOMP_C_SOURCES CONFIGURE_DEPENDS
    "${NP3F_GENERATED_DIR}/funcs_*.c"
)

list(LENGTH RECOMP_C_SOURCES RECOMP_C_SOURCE_COUNT)
if(RECOMP_C_SOURCE_COUNT EQUAL 0)
    message(FATAL_ERROR "No generated funcs_*.c sources were found in ${NP3F_GENERATED_DIR}.")
endif()

message(STATUS "NP3F generated directory : ${NP3F_GENERATED_DIR}")
message(STATUS "N64Recomp include        : ${N64RECOMP_INCLUDE_DIR}")
message(STATUS "Generated C translation units: ${RECOMP_C_SOURCE_COUNT}")

add_library(AeroNP3FGenerated STATIC
    ${RECOMP_C_SOURCES}
    "${NP3F_GENERATED_DIR}/lookup.cpp"
)

target_include_directories(AeroNP3FGenerated PRIVATE
    "${NP3F_GENERATED_DIR}"
    "${N64RECOMP_INCLUDE_DIR}"
)

target_compile_definitions(AeroNP3FGenerated PRIVATE
    _CRT_SECURE_NO_WARNINGS
)

set(NP3F_MEMORY_COMPAT_HEADER
    "${CMAKE_CURRENT_SOURCE_DIR}/np3f_memory_compat.h"
)

if(NOT EXISTS "${NP3F_MEMORY_COMPAT_HEADER}")
    message(FATAL_ERROR "Missing NP3F memory compatibility header: ${NP3F_MEMORY_COMPAT_HEADER}")
endif()

if(MSVC)
    # This target is a syntax/codegen smoke build, not the final optimized host.
    # /Od keeps the first full compile substantially lighter while /bigobj
    # gives the large generated translation units plenty of section headroom.
    target_compile_options(AeroNP3FGenerated PRIVATE
        "/FI${NP3F_MEMORY_COMPAT_HEADER}"
        /Od
        /bigobj
        /W1
        /wd4101
        /wd4244
        /wd4267
    )
else()
    target_compile_options(AeroNP3FGenerated PRIVATE
        -include "${NP3F_MEMORY_COMPAT_HEADER}"
    )
endif()

set_target_properties(AeroNP3FGenerated PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    ARCHIVE_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/lib"
    ARCHIVE_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/lib"
)
