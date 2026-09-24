cmake_minimum_required(VERSION 3.20)

project(AeroStadium2FRNative
    VERSION 0.1.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(aero_runtime STATIC
    src/fixed_step_clock.cpp
)

target_include_directories(aero_runtime
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

if(MSVC)
    target_compile_options(aero_runtime PRIVATE /W4 /permissive-)
else()
    target_compile_options(aero_runtime PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(aero_runtime_probe
    src/runtime_probe.cpp
)

target_link_libraries(aero_runtime_probe
    PRIVATE
        aero_runtime
)

if(MSVC)
    target_compile_options(aero_runtime_probe PRIVATE /W4 /permissive-)
else()
    target_compile_options(aero_runtime_probe PRIVATE -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME aero_runtime_probe COMMAND aero_runtime_probe)
