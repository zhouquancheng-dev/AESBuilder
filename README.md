# AESBuilder

AES 加密 SO 库一键构建工具，为 Android 项目快速生成独立的 AES 加密/解密 Native 库。

只需编辑一个 `config.json`，运行一条命令，即可自动生成包含签名校验、防调试、模拟器检测的加密 SO 库。

## 功能特性

- AES-128 加密/解密（CBC 模式 + Base64）
- MD5 签名（可选，输入拼接 sign_key 后取 MD5 摘要）
- APK 签名校验（防二次打包）
- 反调试检测
- 模拟器检测
- 密钥混淆存储（Base64 + 干扰字符）
- 支持自定义包名、类名、方法名、SO 名
- 支持 armeabi-v7a / arm64-v8a 架构

## 环境要求

- Python 3.6+
- JDK 17 或 21
- Android SDK（含 NDK 和 CMake）

## 快速开始

### 1. 编辑配置

```json
{
    "package_name": "com.example.myapp",
    "signature_hash": -2043803321,
    "aes_key": "1234567890abcdef",
    "interference_char": "N",
    "so_name": "MyEncrypt",
    "jni_class_package": "com.example.myapp.utils",
    "jni_class_name": "MyEncrypt",
    "method_encode": "my_encode",
    "method_decode": "my_decode",
    "method_check": "my_check",
    "sign_key": "&key=your_sign_key_here",
    "method_sign": "my_sign",
    "abi_filters": ["armeabi-v7a", "arm64-v8a"]
}
```

> `sign_key` 和 `method_sign` 为可选字段，不需要 MD5 签名功能可以删除这两行。

### 2. 运行构建

```bash
# 正式构建：生成目标项目的 SO 库
python build_so.py

# 测试模式：额外构建测试 APK
python build_so.py --test
```

### 3. 获取产物

构建完成后，从 `output/` 目录获取 SO 文件和 Java JNI 类：

```
output/
├── armeabi-v7a/
│   └── libMyEncrypt.so
├── arm64-v8a/
│   └── libMyEncrypt.so
└── java/
    └── com/example/myapp/utils/
        └── MyEncrypt.java
```

将 SO 文件放到目标项目的 `jniLibs/` 目录，Java 文件复制到对应包路径下即可使用。

### 4. 调用示例

```kotlin
// 加密
val encrypted = MyEncrypt.my_encode(context, "hello world")

// 解密
val decrypted = MyEncrypt.my_decode(context, encrypted)

// 签名校验（返回 1 表示通过）
val result = MyEncrypt.my_check(context)

// MD5 签名（需配置 sign_key 和 method_sign）
val signed = MyEncrypt.my_sign(context, "data_to_sign")
```

## 测试模式

`--test` 模式会额外构建测试 APK（`app:assembleDebug`）。

要让测试 app 通过签名校验，需将 `config.json` 中的 `package_name` 和 `signature_hash` 设为测试 app 的值：

1. 将 `package_name` 设为 `"com.example.myapp"`
2. 运行测试 app，在 Logcat 过滤 `AES_DEBUG` 获取签名哈希
3. 将哈希值填入 `signature_hash`
4. 运行 `python build_so.py --test`

正式构建时改回目标项目的值即可。

## 项目结构

```
AESBuilder/
├── config.json              ← 唯一需要编辑的配置文件
├── build_so.py              ← 构建脚本
├── templates/               ← 模板文件（脚本自动替换占位符）
├── lib_module/              ← Android Library 模块（native 源码）
├── app/                     ← 测试模块（加解密测试 + 签名哈希获取）
└── output/                  ← 构建产物输出
```

## 配置说明

| 字段 | 说明 | 备注 |
|------|------|------|
| `package_name` | 目标 APP 的 applicationId | 必须与目标项目一致 |
| `signature_hash` | APK 签名的 hashCode | 用于防二次打包校验 |
| `aes_key` | AES-128 密钥 | 必须 16 个 ASCII 字符 |
| `so_name` | SO 库名称 | 最终文件为 `lib<so_name>.so` |
| `jni_class_package` | JNI 类的包名 | 生成的 Java 类和 SO 的 JNI 注册路径均使用此包名 |
| `jni_class_name` | JNI 类名 | 按目标项目调整 |
| `method_encode` | 加密方法名 | 可自定义 |
| `method_decode` | 解密方法名 | 可自定义 |
| `method_check` | 签名校验方法名 | 可自定义 |
| `sign_key` | MD5 签名拼接的密钥 | 可选，不填则不生成 sign 功能 |
| `method_sign` | MD5 签名方法名 | 可选，与 sign_key 必须同时配置 |
| `abi_filters` | 目标 CPU 架构 | 支持 armeabi-v7a、arm64-v8a |

> 详细使用说明请参阅 [使用说明.md](使用说明.md)

## License

MIT
