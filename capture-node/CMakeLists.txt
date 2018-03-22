cmake_minimum_required(VERSION 3.5)

set(CMAKE_CXX_STANDARD 11)

project("avaCapture")

include(GitUtils.cmake)
Git_GetCommitVersion()

include(ExternalProject)

#add_definitions(-D_GLIBCXX_USE_CXX11_ABI=1)
#add_definitions(-DRAPIDJSON_HAS_STDSTRING -DRAPIDJSON_HAS_CXX11_RVALUE_REFS)

file(GLOB SOURCES "source/*.cpp")

#Include OpenCV
find_package(OpenCV 3.2.0 REQUIRED)
include_directories(${OpenCV_INCLUDE_DIRS})

find_package(OpenSSL REQUIRED)

find_package(PythonLibs 2.7 REQUIRED)
include_directories(${PYTHON_INCLUDE_DIRS})

# Include Boost 1.58
set(Boost_USE_STATIC_LIBS OFF)
set(Boost_USE_MULTITHREADED ON)
set(Boost_USE_STATIC_RUNTIME OFF)
find_package(Boost 1.58.0 REQUIRED COMPONENTS thread filesystem program_options)
include_directories(${Boost_INCLUDE_DIRS})

# Portaudio
include (FindPortaudio.cmake)

if (PORTAUDIO_FOUND)
    include_directories(${PORTAUDIO_INCLUDE_DIRS})
    add_definitions(-DWITH_PORTAUDIO)
else (PORTAUDIO_FOUND)
    set(PORTAUDIO_LIBRARIES "")
endif (PORTAUDIO_FOUND)

# websocketpp
set(WEBSOCKETPP_ROOT ${CMAKE_BINARY_DIR}/thirdparty/websocketpp)
set(WEBSOCKETPP_INCLUDE_DIR ${WEBSOCKETPP_ROOT}/src/websocketpp_external)
ExternalProject_Add(websocketpp_external
    PREFIX ${WEBSOCKETPP_ROOT}
    GIT_REPOSITORY "https://github.com/zaphoyd/websocketpp.git"
    BUILD_COMMAND ""
    INSTALL_COMMAND ""
    CONFIGURE_COMMAND ""
)
include_directories(${WEBSOCKETPP_INCLUDE_DIR})
message(${WEBSOCKETPP_INCLUDE_DIR})

# set(CMAKE_BUILD_TYPE Debug)

add_executable(avaCapture ${SOURCES})
add_dependencies(avaCapture websocketpp_external)

target_link_libraries(avaCapture ${PYTHON_LIBRARY} ${OpenCV_LIBS} ${Boost_LIBRARIES} ${PORTAUDIO_LIBRARIES} avcodec avformat avutil tbb m3api ${OPENSSL_LIBRARIES})

