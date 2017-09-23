
function(Git_GetCommitVersion)
  
  execute_process(
    COMMAND git describe --tags --dirty --long --always
    OUTPUT_VARIABLE GIT_DESCRIBE
    OUTPUT_STRIP_TRAILING_WHITESPACE)

  set(GIT_COMMIT_VERSION ${GIT_DESCRIBE})

  MESSAGE( STATUS "Git Commit Version: ${GIT_COMMIT_VERSION}" )
  CONFIGURE_FILE(${CMAKE_CURRENT_SOURCE_DIR}/GitUtils.cmake.in ${CMAKE_CURRENT_SOURCE_DIR}/source/build_generated.h @ONLY)
endfunction()


