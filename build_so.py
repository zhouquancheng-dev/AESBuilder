#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AESBuilder - 一键生成 AES 加密 SO 库
用法: python build_so.py [config.json路径] [--test] [--generate-only]

--test           额外构建测试 app (app:assembleDebug)
--generate-only  仅生成源文件，不执行 Gradle 构建和产物复制（供 Gradle preBuild 调用）
"""

import json
import os
import re
import sys
import base64
import shutil
import subprocess


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
LIB_MODULE_DIR = os.path.join(SCRIPT_DIR, "lib_module")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# 测试 app 固定包名（与 build.gradle.kts 中 applicationId 一致）
APP_PACKAGE = "com.example.myapp"


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

    # AES 密钥长度校验（必须是 16 个 ASCII 可打印字符）
    aes_key = config["aes_key"]
    if len(aes_key) != 16:
        raise ValueError(f"aes_key 必须是16个字符，当前长度: {len(aes_key)}")
    if not all(32 <= ord(c) <= 126 for c in aes_key):
        raise ValueError("aes_key 必须是 ASCII 可打印字符")

    # 干扰字符校验（必须是 ASCII 可打印字符，且不能是单引号/反斜杠，避免 C 字面量问题）
    ic = config["interference_char"]
    if len(ic) != 1:
        raise ValueError(f"interference_char 必须是单个字符，当前: '{ic}'")
    if not (32 <= ord(ic) <= 126) or ic in ("'", "\\"):
        raise ValueError(f"interference_char 不能是单引号、反斜杠或非 ASCII 字符，当前: '{ic}'")

    # 标识符校验（C/Java 合法标识符）
    id_re = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    for field in ("so_name", "jni_class_name", "method_encode", "method_decode", "method_check"):
        val = config[field]
        if not val or not id_re.match(val):
            raise ValueError(f"{field} 必须是合法的 C/Java 标识符: '{val}'")

    # 包名校验（Java 包名格式）
    pkg_re = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$')
    for field in ("package_name", "jni_class_package"):
        val = config[field]
        if not val or not pkg_re.match(val):
            raise ValueError(f"{field} 必须是合法的 Java 包名（至少两段）: '{val}'")

    # abi_filters 校验
    valid_abis = {"armeabi-v7a", "arm64-v8a", "x86", "x86_64"}
    if not isinstance(config["abi_filters"], list) or len(config["abi_filters"]) == 0:
        raise ValueError("abi_filters 必须是非空数组")
    for abi in config["abi_filters"]:
        if abi not in valid_abis:
            raise ValueError(f"abi_filters 包含不支持的架构: '{abi}'（支持: {', '.join(sorted(valid_abis))}）")

    # sign 功能校验（可选，但 sign_key 和 method_sign 必须同时配置）
    has_sign_key = bool(config.get("sign_key"))
    has_method_sign = bool(config.get("method_sign"))
    if has_sign_key != has_method_sign:
        raise ValueError("sign_key 和 method_sign 必须同时配置（或同时留空/不填）")
    if has_method_sign:
        val = config["method_sign"]
        if not id_re.match(val):
            raise ValueError(f"method_sign 必须是合法的 C/Java 标识符: '{val}'")

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

    # 数组大小 = 字符串长度 + 1（为 '\0' 终止符留空间，供 strlen 使用）
    array_size = len(full_str) + 1

    # 生成逐字符赋值代码
    lines = []
    for ch in full_str:
        lines.append(f"    s[n++] = '{ch}';")

    return array_size, "\n".join(lines)


def has_sign(config):
    """判断是否启用 sign 功能"""
    return bool(config.get("sign_key")) and bool(config.get("method_sign"))


def get_sign_replacements(config):
    """根据 sign 配置生成模板占位符替换值（有 sign 则生成代码，无则为空）"""
    if not has_sign(config):
        return {
            "{{SIGN_KEY_LINE}}": "",
            "{{SIGN_INCLUDE}}": "",
            "{{SIGN_FUNCTION}}": "",
            "{{SIGN_METHOD_ENTRY}}": "",
            "{{SIGN_CMAKE_SOURCES}}": "",
            "{{SIGN_METHOD_DECLARATION}}": "",
            "{{METHOD_SIGN}}": "",
            "{{SIGN_BUTTON}}": "",
        }

    method_sign = config["method_sign"]
    sign_key = config["sign_key"]
    jni_class_name = config.get("jni_class_name", "")

    sign_function = '''
JNIEXPORT jstring JNICALL sign(JNIEnv *env, jobject instance, jobject context, jstring str_) {

    //先进行apk被 二次打包的校验
    if (check_signature(env, instance, context) != 1 || check_is_emulator(env) != 1) {
        const char *str = UNSIGNATURE;
        return charToJstring(env, str);
    }

    const char *str = (*env)->GetStringUTFChars(env, str_, JNI_FALSE);

    // 拼接 str + app_signkey
    int str_len = strlen(str);
    int key_len = strlen(app_signkey);
    char *combined = (char *)malloc(str_len + key_len + 1);
    strcpy(combined, str);
    strcat(combined, app_signkey);

    // 计算 MD5
    MD5_CTX md5;
    MD5Init(&md5);
    MD5Update(&md5, (unsigned char *)combined, strlen(combined));
    unsigned char digest[16];
    MD5Final(&md5, digest);

    free(combined);
    (*env)->ReleaseStringUTFChars(env, str_, str);

    // 转为32位十六进制字符串
    char hex_result[33];
    for (int i = 0; i < 16; i++) {
        sprintf(hex_result + i * 2, "%02x", digest[i]);
    }
    hex_result[32] = '\\0';

    return (*env)->NewStringUTF(env, hex_result);
}'''

    sign_button = f'''
        // Sign (MD5签名)
        findViewById<View>(R.id.card_sign).visibility = View.VISIBLE
        val tvSignResult = findViewById<TextView>(R.id.tv_sign_result)
        val btnSign = findViewById<MaterialButton>(R.id.btn_sign)
        btnSign.setOnClickListener {{
            val input = etInput.text?.toString()?.trim().orEmpty()
            if (input.isEmpty()) {{
                Toast.makeText(this, "请输入待签名字符串", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }}
            try {{
                val signResult = {jni_class_name}.{method_sign}(this, input)
                tvSignResult.text = signResult
            }} catch (e: Exception) {{
                tvSignResult.text = "签名失败: %s".format(e.message)
            }}
        }}'''

    return {
        "{{SIGN_KEY_LINE}}": f'static const char *app_signkey = "{sign_key}";',
        "{{SIGN_INCLUDE}}": '#include "md5.h"',
        "{{SIGN_FUNCTION}}": sign_function,
        "{{SIGN_METHOD_ENTRY}}": f'        {{"{method_sign}",         "(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/String;", (void *) sign}},',
        "{{SIGN_CMAKE_SOURCES}}": "             src/main/cpp/md5.h\n             src/main/cpp/md5.c",
        "{{SIGN_METHOD_DECLARATION}}": f'\n    /**\n     * MD5签名\n     */\n    public static native String {method_sign}(Object context, String str);',
        "{{METHOD_SIGN}}": method_sign,
        "{{SIGN_BUTTON}}": sign_button,
    }


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
    sign_repl = get_sign_replacements(config)

    # 1. 生成 checksignature.h
    checksig_content = render_template("checksignature.h.tmpl", {
        "{{PACKAGE_NAME}}": config["package_name"],
        "{{SIGNATURE_HASH}}": str(config["signature_hash"]),
        "{{SIGN_KEY_LINE}}": sign_repl["{{SIGN_KEY_LINE}}"],
    })
    with open(os.path.join(cpp_dir, "checksignature.h"), "w", encoding="utf-8") as f:
        f.write(checksig_content)
    print(f"  [OK] checksignature.h")

    # 2. 生成 JNIEncrypt.c
    jni_class_package = config["jni_class_package"]
    jni_class_path = jni_class_package.replace(".", "/") + "/" + config["jni_class_name"]
    array_size, key_char_lines = generate_key_code(config["aes_key"], config["interference_char"])

    jni_content = render_template("JNIEncrypt.c.tmpl", {
        "{{JNI_CLASS_PATH}}": jni_class_path,
        "{{KEY_ARRAY_SIZE}}": str(array_size),
        "{{KEY_CHAR_LINES}}": key_char_lines,
        "{{METHOD_CHECK}}": config["method_check"],
        "{{METHOD_DECODE}}": config["method_decode"],
        "{{METHOD_ENCODE}}": config["method_encode"],
        "{{SIGN_INCLUDE}}": sign_repl["{{SIGN_INCLUDE}}"],
        "{{SIGN_FUNCTION}}": sign_repl["{{SIGN_FUNCTION}}"],
        "{{SIGN_METHOD_ENTRY}}": sign_repl["{{SIGN_METHOD_ENTRY}}"],
    })
    with open(os.path.join(cpp_dir, "JNIEncrypt.c"), "w", encoding="utf-8") as f:
        f.write(jni_content)
    print(f"  [OK] JNIEncrypt.c")

    # 3. 生成 CMakeLists.txt
    cmake_content = render_template("CMakeLists.txt.tmpl", {
        "{{SO_NAME}}": config["so_name"],
        "{{SIGN_CMAKE_SOURCES}}": sign_repl["{{SIGN_CMAKE_SOURCES}}"],
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
        "{{PACKAGE}}": jni_class_package,
        "{{CLASS_NAME}}": config["jni_class_name"],
        "{{SO_NAME}}": config["so_name"],
        "{{METHOD_ENCODE}}": config["method_encode"],
        "{{METHOD_DECODE}}": config["method_decode"],
        "{{METHOD_CHECK}}": config["method_check"],
        "{{SIGN_METHOD_DECLARATION}}": sign_repl["{{SIGN_METHOD_DECLARATION}}"],
    })

    # 清理 lib_module java 目录，避免残留旧包
    java_base_dir = os.path.join(LIB_MODULE_DIR, "src", "main", "java")
    if os.path.exists(java_base_dir):
        shutil.rmtree(java_base_dir)

    java_pkg_dir = os.path.join(java_base_dir, *jni_class_package.split("."))
    os.makedirs(java_pkg_dir, exist_ok=True)

    java_file_path = os.path.join(java_pkg_dir, config["jni_class_name"] + ".java")
    with open(java_file_path, "w", encoding="utf-8") as f:
        f.write(java_content)
    print(f"  [OK] {config['jni_class_name']}.java ({jni_class_package})")

    # 6. 生成 MainActivity.kt（测试 app）
    activity_content = render_template("MainActivity.kt.tmpl", {
        "{{APP_PACKAGE}}": APP_PACKAGE,
        "{{JNI_CLASS_PACKAGE}}": jni_class_package,
        "{{JNI_CLASS_NAME}}": config["jni_class_name"],
        "{{METHOD_ENCODE}}": config["method_encode"],
        "{{METHOD_DECODE}}": config["method_decode"],
        "{{METHOD_CHECK}}": config["method_check"],
        "{{SIGN_BUTTON}}": sign_repl["{{SIGN_BUTTON}}"],
    })

    activity_dir = os.path.join(
        SCRIPT_DIR, "app", "src", "main", "kotlin",
        *APP_PACKAGE.split(".")
    )
    os.makedirs(activity_dir, exist_ok=True)

    activity_path = os.path.join(activity_dir, "MainActivity.kt")
    with open(activity_path, "w", encoding="utf-8") as f:
        f.write(activity_content)
    print(f"  [OK] MainActivity.kt ({APP_PACKAGE})")


def build_so(test_mode=False):
    """调用 Gradle 编译"""
    if sys.platform == "win32":
        gradlew = os.path.join(SCRIPT_DIR, "gradlew.bat")
    else:
        gradlew = os.path.join(SCRIPT_DIR, "gradlew")

    # 先 clean native 构建缓存，避免 CMake 使用旧的 .o 文件
    clean_cmd = [gradlew, ":lib_module:externalNativeBuildCleanRelease"]
    print(f"\n>>> 清理 native 缓存: {' '.join(clean_cmd)}")
    subprocess.run(clean_cmd, cwd=SCRIPT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    tasks = [":lib_module:assembleRelease"]
    if test_mode:
        tasks.append(":app:assembleDebug")

    cmd = [gradlew] + tasks
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
    jni_class_package = config["jni_class_package"]
    java_pkg_dir = os.path.join(
        LIB_MODULE_DIR, "src", "main", "java",
        *jni_class_package.split(".")
    )
    java_file = os.path.join(java_pkg_dir, config["jni_class_name"] + ".java")
    if os.path.exists(java_file):
        java_out_dir = os.path.join(OUTPUT_DIR, "java",
                                     *jni_class_package.split("."))
        os.makedirs(java_out_dir, exist_ok=True)
        shutil.copy2(java_file, java_out_dir)
        print(f"  [OK] {config['jni_class_name']}.java")

    return so_count


def main():
    # 解析参数
    flags = {"--test", "--generate-only"}
    args = [a for a in sys.argv[1:] if a not in flags]
    test_mode = "--test" in sys.argv
    generate_only = "--generate-only" in sys.argv

    config_path = args[0] if args else os.path.join(SCRIPT_DIR, "config.json")

    print("=" * 50)
    if test_mode:
        print("  AESBuilder - SO 库一键构建工具 [测试模式]")
    else:
        print("  AESBuilder - SO 库一键构建工具")
    print("=" * 50)

    # 1. 读取配置
    print(f"\n[1/4] 读取配置: {config_path}")
    config = load_config(config_path)

    print(f"  包名: {config['package_name']}")
    print(f"  SO名: {config['so_name']}")
    print(f"  JNI类: {config['jni_class_package']}.{config['jni_class_name']}")
    print(f"  ABI: {', '.join(config['abi_filters'])}")
    if has_sign(config):
        print(f"  Sign: {config['method_sign']} (已启用)")

    # 2. 生成文件
    print(f"\n[2/4] 生成源文件...")
    generate_files(config)

    if generate_only:
        print("\n[--generate-only] 仅生成源文件，跳过构建和产物复制")
        return

    # 3. Gradle 构建
    print(f"\n[3/4] Gradle 构建...")
    build_so(test_mode=test_mode)

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
    if test_mode:
        print("  [测试模式] 已构建测试 APK: app:assembleDebug")
    print("=" * 50)


if __name__ == "__main__":
    main()
