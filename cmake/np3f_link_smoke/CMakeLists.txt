cmake_minimum_required(VERSION 3.20)

project(AeroStadium2LinkSmoke LANGUAGES C CXX)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT DEFINED NP3F_GENERATED_LIB)
    message(FATAL_ERROR "NP3F_GENERATED_LIB was not provided.")
endif()
if(NOT DEFINED NP3F_GENERATED_DIR)
    message(FATAL_ERROR "NP3F_GENERATED_DIR was not provided.")
endif()
if(NOT DEFINED N64MODERNRUNTIME_SOURCE_DIR)
    message(FATAL_ERROR "N64MODERNRUNTIME_SOURCE_DIR was not provided.")
endif()

file(TO_CMAKE_PATH "${NP3F_GENERATED_LIB}" NP3F_GENERATED_LIB)
file(TO_CMAKE_PATH "${NP3F_GENERATED_DIR}" NP3F_GENERATED_DIR)
file(TO_CMAKE_PATH "${N64MODERNRUNTIME_SOURCE_DIR}" N64MODERNRUNTIME_SOURCE_DIR)

if(NOT EXISTS "${NP3F_GENERATED_LIB}")
    message(FATAL_ERROR "Generated NP3F library not found: ${NP3F_GENERATED_LIB}")
endif()
if(NOT EXISTS "${N64MODERNRUNTIME_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "N64ModernRuntime source not found: ${N64MODERNRUNTIME_SOURCE_DIR}")
endif()

add_subdirectory("${N64MODERNRUNTIME_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/runtime")

add_library(AeroNP3FGenerated STATIC IMPORTED GLOBAL)
set_target_properties(AeroNP3FGenerated PROPERTIES IMPORTED_LOCATION "${NP3F_GENERATED_LIB}")

add_executable(AeroStadium2 "${CMAKE_CURRENT_SOURCE_DIR}/main.cpp")

target_include_directories(AeroStadium2 PRIVATE
    "${NP3F_GENERATED_DIR}"
    "${N64MODERNRUNTIME_SOURCE_DIR}/N64Recomp/include"
    "${N64MODERNRUNTIME_SOURCE_DIR}/ultramodern/include"
    "${N64MODERNRUNTIME_SOURCE_DIR}/librecomp/include"
)

target_link_libraries(AeroStadium2 PRIVATE AeroNP3FGenerated librecomp ultramodern)

if(MSVC)
    target_link_options(AeroStadium2 PRIVATE "/WHOLEARCHIVE:${NP3F_GENERATED_LIB}")
endif()

set_target_properties(AeroStadium2 PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
)