#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AESBuilder - 一键生成 AES 加密 SO 库
用法: python build_so.py [config.json路径]
"""

import json
import os
import sys
import base64
import shutil
import subprocess


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
LIB_MODULE_DIR = os.path.join(SCRIPT_DIR, "lib_module")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")


def load_config(config_path):
    """读取并校验 config.json"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 过滤注释字段
    config = {k: v for k, v in config.items() if not k.startswith("_comment")}

    # 必填项检查
    required_fields = [
        "package_name", "signature_hash", "aes_key", "interference_char",
        "so_name", "jni_class_package", "jni_class_name",
        "method_encode", "method_decode", "method_check", "abi_filters"
    ]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"config.json 缺少必填项: {field}")

    # AES 密钥长度校验
    if len(config["aes_key"]) != 16:
        raise ValueError(f"aes_key 必须是16个字符，当前长度: {len(config['aes_key'])}")

    # 干扰字符校验
    if len(config["interference_char"]) != 1:
        raise ValueError(f"interference_char 必须是单个字符，当前: '{config['interference_char']}'")

    # abi_filters 校验
    if not isinstance(config["abi_filters"], list) or len(config["abi_filters"]) == 0:
        raise ValueError("abi_filters 必须是非空数组")

    return config


def generate_key_code(aes_key, interference_char):
    """
    将 AES 密钥 Base64 编码，加干扰字符，生成逐字符赋值的 C 代码。
    返回 (array_size, char_lines)
    """
    # Base64 编码
    b64_encoded = base64.b64encode(aes_key.encode("utf-8")).decode("utf-8")

    # 加干扰字符到前面
    full_str = interference_char + b64_encoded

    # 数组大小 = 字符串长度 (不含\0，因为原代码用的就是裸数组)
    array_size = len(full_str)

    # 生成逐字符赋值代码
    lines = []
    for ch in full_str:
        lines.append(f"    s[n++] = '{ch}';")

    return array_size, "\n".join(lines)


def render_template(template_name, replacements):
    """读取模板文件并替换占位符"""
    tmpl_path = os.path.join(TEMPLATES_DIR, template_name)
    with open(tmpl_path, "r", encoding="utf-8") as f:
        content = f.read()

    for key, value in replacements.items():
        content = content.replace(key, str(value))

    return content


def generate_files(config):
    """根据配置生成所有需要的文件"""
    cpp_dir = os.path.join(LIB_MODULE_DIR, "src", "main", "cpp")

    # 1. 生成 checksignature.h
    checksig_content = render_template("checksignature.h.tmpl", {
        "{{PACKAGE_NAME}}": config["package_name"],
        "{{SIGNATURE_HASH}}": str(config["signature_hash"]),
    })
    with open(os.path.join(cpp_dir, "checksignature.h"), "w", encoding="utf-8") as f:
        f.write(checksig_content)
    print(f"  [OK] checksignature.h")

    # 2. 生成 JNIEncrypt.c
    jni_class_path = config["jni_class_package"].replace(".", "/") + "/" + config["jni_class_name"]
    array_size, key_char_lines = generate_key_code(config["aes_key"], config["interference_char"])

    jni_content = render_template("JNIEncrypt.c.tmpl", {
        "{{JNI_CLASS_PATH}}": jni_class_path,
        "{{KEY_ARRAY_SIZE}}": str(array_size),
        "{{KEY_CHAR_LINES}}": key_char_lines,
        "{{METHOD_CHECK}}": config["method_check"],
        "{{METHOD_DECODE}}": config["method_decode"],
        "{{METHOD_ENCODE}}": config["method_encode"],
    })
    with open(os.path.join(cpp_dir, "JNIEncrypt.c"), "w", encoding="utf-8") as f:
        f.write(jni_content)
    print(f"  [OK] JNIEncrypt.c")

    # 3. 生成 CMakeLists.txt
    cmake_content = render_template("CMakeLists.txt.tmpl", {
        "{{SO_NAME}}": config["so_name"],
    })
    with open(os.path.join(LIB_MODULE_DIR, "CMakeLists.txt"), "w", encoding="utf-8") as f:
        f.write(cmake_content)
    print(f"  [OK] CMakeLists.txt")

    # 4. 生成 build.gradle.kts
    abi_str = ", ".join([f'"{abi}"' for abi in config["abi_filters"]])
    gradle_content = render_template("build.gradle.kts.tmpl", {
        "{{ABI_FILTERS}}": abi_str,
    })
    with open(os.path.join(LIB_MODULE_DIR, "build.gradle.kts"), "w", encoding="utf-8") as f:
        f.write(gradle_content)
    print(f"  [OK] build.gradle.kts")

    # 5. 生成 Java JNI 类
    java_content = render_template("JniEncrypt.java.tmpl", {
        "{{PACKAGE}}": config["jni_class_package"],
        "{{CLASS_NAME}}": config["jni_class_name"],
        "{{SO_NAME}}": config["so_name"],
        "{{METHOD_ENCODE}}": config["method_encode"],
        "{{METHOD_DECODE}}": config["method_decode"],
        "{{METHOD_CHECK}}": config["method_check"],
    })

    # 创建 Java 包目录
    java_pkg_dir = os.path.join(
        LIB_MODULE_DIR, "src", "main", "java",
        *config["jni_class_package"].split(".")
    )
    os.makedirs(java_pkg_dir, exist_ok=True)

    java_file_path = os.path.join(java_pkg_dir, config["jni_class_name"] + ".java")
    with open(java_file_path, "w", encoding="utf-8") as f:
        f.write(java_content)
    print(f"  [OK] {config['jni_class_name']}.java")


def build_so():
    """调用 Gradle 编译"""
    if sys.platform == "win32":
        gradlew = os.path.join(SCRIPT_DIR, "gradlew.bat")
    else:
        gradlew = os.path.join(SCRIPT_DIR, "gradlew")

    cmd = [gradlew, ":lib_module:assembleRelease"]
    print(f"\n>>> 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)

    if result.returncode != 0:
        print("\n[ERROR] Gradle 构建失败！")
        sys.exit(1)

    print("\n[OK] Gradle 构建成功")


def copy_output(config):
    """复制 SO 和 Java 类到 output 目录"""
    # 清空并重建 output 目录
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # 复制 SO 文件 - 尝试多个可能的路径 (AGP 4.x vs 7.x vs 8.x)
    so_name = f"lib{config['so_name']}.so"
    so_search_bases = [
        # AGP 8.x (stripped)
        os.path.join(LIB_MODULE_DIR, "build", "intermediates", "stripped_native_libs", "release", "out", "lib"),
        # AGP 8.x (merged)
        os.path.join(LIB_MODULE_DIR, "build", "intermediates", "merged_native_libs", "release", "out", "lib"),
        # AGP 4.x
        os.path.join(LIB_MODULE_DIR, "build", "intermediates", "cmake", "release", "obj"),
    ]

    # 也搜索 cxx 目录下的 RelWithDebInfo (AGP 8.x with cmake)
    cxx_dir = os.path.join(LIB_MODULE_DIR, "build", "intermediates", "cxx")
    if os.path.exists(cxx_dir):
        for root, dirs, files in os.walk(cxx_dir):
            if "obj" in dirs:
                so_search_bases.append(os.path.join(root, "obj"))

    so_count = 0
    for abi in config["abi_filters"]:
        found = False
        for base_dir in so_search_bases:
            so_src = os.path.join(base_dir, abi, so_name)
            if os.path.exists(so_src):
                abi_out_dir = os.path.join(OUTPUT_DIR, abi)
                os.makedirs(abi_out_dir, exist_ok=True)
                shutil.copy2(so_src, abi_out_dir)
                so_count += 1
                print(f"  [OK] {abi}/{so_name}")
                found = True
                break
        if not found:
            print(f"  [WARN] 未找到 {abi}/{so_name}")

    # 复制 Java 类
    java_pkg_dir = os.path.join(
        LIB_MODULE_DIR, "src", "main", "java",
        *config["jni_class_package"].split(".")
    )
    java_file = os.path.join(java_pkg_dir, config["jni_class_name"] + ".java")
    if os.path.exists(java_file):
        java_out_dir = os.path.join(OUTPUT_DIR, "java",
                                     *config["jni_class_package"].split("."))
        os.makedirs(java_out_dir, exist_ok=True)
        shutil.copy2(java_file, java_out_dir)
        print(f"  [OK] {config['jni_class_name']}.java")

    return so_count


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCRIPT_DIR, "config.json")

    print("=" * 50)
    print("  AESBuilder - SO 库一键构建工具")
    print("=" * 50)

    # 1. 读取配置
    print(f"\n[1/4] 读取配置: {config_path}")
    config = load_config(config_path)
    print(f"  包名: {config['package_name']}")
    print(f"  SO名: {config['so_name']}")
    print(f"  JNI类: {config['jni_class_package']}.{config['jni_class_name']}")
    print(f"  ABI: {', '.join(config['abi_filters'])}")

    # 2. 生成文件
    print(f"\n[2/4] 生成源文件...")
    generate_files(config)

    # 3. Gradle 构建
    print(f"\n[3/4] Gradle 构建...")
    build_so()

    # 4. 复制输出
    print(f"\n[4/4] 复制构建产物到 output/...")
    so_count = copy_output(config)

    # 完成
    print("\n" + "=" * 50)
    if so_count > 0:
        print(f"  构建完成! 共生成 {so_count} 个 SO 文件")
        print(f"  输出目录: {OUTPUT_DIR}")
    else:
        print("  [WARN] 未找到 SO 文件，请检查构建日志")
    print("=" * 50)


if __name__ == "__main__":
    main()
