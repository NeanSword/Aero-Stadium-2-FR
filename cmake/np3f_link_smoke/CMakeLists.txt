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
    RT64_SOURCE_DIR
)
    if(NOT DEFINED ${required_var})
        message(FATAL_ERROR "${required_var} was not provided.")
    endif()
endforeach()

file(TO_CMAKE_PATH "${NP3F_GENERATED_LIB}" NP3F_GENERATED_LIB)
file(TO_CMAKE_PATH "${NP3F_GENERATED_DIR}" NP3F_GENERATED_DIR)
file(TO_CMAKE_PATH "${N64MODERNRUNTIME_SOURCE_DIR}" N64MODERNRUNTIME_SOURCE_DIR)
file(TO_CMAKE_PATH "${N64MODERNRUNTIME_BUILD_DIR}" N64MODERNRUNTIME_BUILD_DIR)
file(TO_CMAKE_PATH "${RT64_SOURCE_DIR}" RT64_SOURCE_DIR)

if(NOT EXISTS "${NP3F_GENERATED_LIB}")
    message(FATAL_ERROR "Generated NP3F library not found: ${NP3F_GENERATED_LIB}")
endif()

if(NOT EXISTS "${N64MODERNRUNTIME_SOURCE_DIR}/N64Recomp/include/recomp.h")
    message(FATAL_ERROR "N64ModernRuntime source tree is incomplete: ${N64MODERNRUNTIME_SOURCE_DIR}")
endif()

if(NOT EXISTS "${N64MODERNRUNTIME_BUILD_DIR}")
    message(FATAL_ERROR "N64ModernRuntime build directory not found: ${N64MODERNRUNTIME_BUILD_DIR}")
endif()

if(NOT EXISTS "${RT64_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "RT64 source tree not found: ${RT64_SOURCE_DIR}. Run windows/setup_rt64_windows.ps1 first.")
endif()

if(NOT EXISTS "${RT64_SOURCE_DIR}/src/hle/rt64_application.h")
    message(FATAL_ERROR "RT64 source tree is incomplete: ${RT64_SOURCE_DIR}")
endif()

set(RT64_STATIC TRUE CACHE BOOL "Build RT64 as a static library" FORCE)
set(RT64_BUILD_EXAMPLES OFF CACHE BOOL "Disable RT64 examples" FORCE)
add_subdirectory("${RT64_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/rt64")

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
    "${CMAKE_CURRENT_SOURCE_DIR}/np3f_runtime_probe.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/np3f_rt64_renderer.cpp"
)

target_include_directories(AeroStadium2 PRIVATE
    "${NP3F_GENERATED_DIR}"
    "${N64MODERNRUNTIME_SOURCE_DIR}/N64Recomp/include"
    "${N64MODERNRUNTIME_SOURCE_DIR}/ultramodern/include"
    "${N64MODERNRUNTIME_SOURCE_DIR}/librecomp/include"
    "${N64MODERNRUNTIME_SOURCE_DIR}/thirdparty"
    "${N64MODERNRUNTIME_SOURCE_DIR}/thirdparty/concurrentqueue"
    "${N64MODERNRUNTIME_SOURCE_DIR}/thirdparty/o1heap"
    "${N64MODERNRUNTIME_SOURCE_DIR}/thirdparty/xxHash"
    "${RT64_SOURCE_DIR}/src"
    "${RT64_SOURCE_DIR}/src/contrib"
    "${RT64_SOURCE_DIR}/src/contrib/D3D12MemoryAllocator/include"
    "${RT64_SOURCE_DIR}/src/contrib/D3D12MemoryAllocator/src"
    "${RT64_SOURCE_DIR}/src/contrib/imgui"
    "${RT64_SOURCE_DIR}/src/contrib/hlslpp/include"
    "${RT64_SOURCE_DIR}/src/contrib/Vulkan-Headers/include"
    "${RT64_SOURCE_DIR}/src/contrib/VulkanMemoryAllocator/include"
    "${RT64_SOURCE_DIR}/src/contrib/mupen64plus-core/src/api"
    "${RT64_SOURCE_DIR}/src/contrib/nativefiledialog-extended/src/include"
    "${RT64_SOURCE_DIR}/src/contrib/dxc/inc"
)

target_link_libraries(AeroStadium2 PRIVATE
    "${NP3F_GENERATED_LIB}"
    ${N64MODERNRUNTIME_LIBS}
    rt64
)

if(WIN32)
    target_link_directories(AeroStadium2 PRIVATE
        "${RT64_SOURCE_DIR}/src/contrib/mupen64plus-win32-deps/SDL2-2.26.3/lib/x64"
    )

    target_link_libraries(AeroStadium2 PRIVATE
        comdlg32
        shell32
        ole32
        SDL2
        SDL2main
    )

    set(RT64_DXCOMPILER_DLL "${RT64_SOURCE_DIR}/src/contrib/dxc/bin/x64/dxcompiler.dll")
    set(RT64_DXIL_DLL "${RT64_SOURCE_DIR}/src/contrib/dxc/bin/x64/dxil.dll")
    set(RT64_SDL2_DLL "${RT64_SOURCE_DIR}/src/contrib/mupen64plus-win32-deps/SDL2-2.26.3/lib/x64/SDL2.dll")

    foreach(runtime_dll IN ITEMS
        "${RT64_DXCOMPILER_DLL}"
        "${RT64_DXIL_DLL}"
        "${RT64_SDL2_DLL}"
    )
        if(NOT EXISTS "${runtime_dll}")
            message(FATAL_ERROR "Required RT64 runtime DLL not found: ${runtime_dll}")
        endif()

        add_custom_command(TARGET AeroStadium2 POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${runtime_dll}"
                "$<TARGET_FILE_DIR:AeroStadium2>"
            VERBATIM
        )
    endforeach()
endif()

if(MSVC)
    target_compile_definitions(AeroStadium2 PRIVATE
        NOMINMAX
        _CRT_SECURE_NO_WARNINGS
        AEROSTADIUM2_WITH_RT64=1
        HLSL_CPU
    )
    target_link_options(AeroStadium2 PRIVATE
        "/WHOLEARCHIVE:${NP3F_GENERATED_LIB}"
        "/MAP:${CMAKE_BINARY_DIR}/bin/AeroStadium2.map"
    )
endif()

set_target_properties(AeroStadium2 PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
)
