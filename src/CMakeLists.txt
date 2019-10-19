# Version chosen arbitrarily
CMAKE_MINIMUM_REQUIRED(VERSION 3.0)

# maybe widgets too
FIND_PACKAGE(Qt5LinguistTools)
INCLUDE(PyQt5TranslationMacros.cmake)
PYQT5_CREATE_TRANSLATION(fnistool_translations_qm ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/FNISTool_en.ts)

add_custom_target(translations ALL DEPENDS ${fnistool_translations_qm})

###############
## Installation

INSTALL(FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/FNISTool.py
        ${CMAKE_CURRENT_SOURCE_DIR}/FNISPatches.py
        DESTINATION bin/plugins)