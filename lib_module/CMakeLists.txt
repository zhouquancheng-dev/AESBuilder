cmake_minimum_required(VERSION 3.4.1)

add_library( # Sets the name of the library.
            MyEncrypt

             # Sets the library as a shared library.
             SHARED

             # Provides a relative path to your source file(s).
             src/main/cpp/JNIEncrypt.c
             src/main/cpp/checksignature.h
             src/main/cpp/checksignature.c
             src/main/cpp/check_emulator.h
             src/main/cpp/check_emulator.c
             src/main/cpp/debugger.h
             src/main/cpp/debugger.c
             src/main/cpp/aes.h
             src/main/cpp/base64.h
             src/main/cpp/aes.c
             src/main/cpp/base64.c
             )

find_library( # Sets the name of the path variable.
              log-lib

              # Specifies the name of the NDK library that
              # you want CMake to locate.
              log )

target_link_libraries( # Specifies the target library.
                       MyEncrypt

                       # included in the NDK.
                       ${log-lib} )
