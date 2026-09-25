cmake_minimum_required(VERSION 3.20)

project(AeroStadium2LinkSmoke LANGUAGES C CXX)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

foreach(required_var
    NP3F_GENERATED_LIB
    NP3F_GENERATED_DIR
    N64MODERNRUNTIME_SOURCE_DIR
    N64MODERNRUNTIME_BUILD_DIR
)
    if(NOT DEFINED ${required_var})
        message(FATAL_ERROR "${required_var} was not provided.")
    endif()
endforeach()

file(TO_CMAKE_PATH "${NP3F_GENERATED_LIB}" NP3F_GENERATED_LIB)
file(TO_CMAKE_PATH "${NP3F_GENERATED_DIR}" NP3F_GENERATED_DIR)
file(TO_CMAKE_PATH "${N64MODERNRUNTIME_SOURCE_DIR}" N64MODERNRUNTIME_SOURCE_DIR)
file(TO_CMAKE_PATH "${N64MODERNRUNTIME_BUILD_DIR}" N64MODERNRUNTIME_BUILD_DIR)

if(NOT EXISTS "${NP3F_GENERATED_LIB}")
    message(FATAL_ERROR "Generated NP3F library not found: ${NP3F_GENERATED_LIB}")
endif()

if(NOT EXISTS "${N64MODERNRUNTIME_SOURCE_DIR}/N64Recomp/include/recomp.h")
    message(FATAL_ERROR "N64ModernRuntime source tree is incomplete: ${N64MODERNRUNTIME_SOURCE_DIR}")
endif()

if(NOT EXISTS "${N64MODERNRUNTIME_BUILD_DIR}")
    message(FATAL_ERROR "N64ModernRuntime build directory not found: ${N64MODERNRUNTIME_BUILD_DIR}")
endif()

file(GLOB_RECURSE N64MODERNRUNTIME_LIBS
    "${N64MODERNRUNTIME_BUILD_DIR}/*.lib"
)

list(FILTER N64MODERNRUNTIME_LIBS INCLUDE REGEX "/Release/.*\\.lib$")
list(FILTER N64MODERNRUNTIME_LIBS EXCLUDE REGEX "AeroStadium2")
list(LENGTH N64MODERNRUNTIME_LIBS RUNTIME_LIB_COUNT)

if(RUNTIME_LIB_COUNT EQUAL 0)
    message(FATAL_ERROR "No prebuilt N64ModernRuntime libraries found under ${N64MODERNRUNTIME_BUILD_DIR}")
endif()

message(STATUS "Using ${RUNTIME_LIB_COUNT} prebuilt N64ModernRuntime libraries")
foreach(runtime_lib IN LISTS N64MODERNRUNTIME_LIBS)
    message(STATUS "  runtime lib: ${runtime_lib}")
endforeach()

add_executable(AeroStadium2
    "${CMAKE_CURRENT_SOURCE_DIR}/main.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/np3f_runtime_compat.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/np3f_register_overlays.cpp"
)

target_include_directories(AeroStadium2 PRIVATE
    "${NP3F_GENERATED_DIR}"
    "${N64MODERNRUNTIME_SOURCE_DIR}/N64Recomp/include"
    "${N64MODERNRUNTIME_SOURCE_DIR}/ultramodern/include"
    "${N64MODERNRUNTIME_SOURCE_DIR}/librecomp/include"
    "${N64MODERNRUNTIME_SOURCE_DIR}/thirdparty"
    "${N64MODERNRUNTIME_SOURCE_DIR}/thirdparty/concurrentqueue"
    "${N64MODERNRUNTIME_SOURCE_DIR}/thirdparty/o1heap"
)

target_link_libraries(AeroStadium2 PRIVATE
    "${NP3F_GENERATED_LIB}"
    ${N64MODERNRUNTIME_LIBS}
)

if(MSVC)
    target_compile_definitions(AeroStadium2 PRIVATE NOMINMAX _CRT_SECURE_NO_WARNINGS)
    target_link_options(AeroStadium2 PRIVATE "/WHOLEARCHIVE:${NP3F_GENERATED_LIB}")
endif()

set_target_properties(AeroStadium2 PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
)
