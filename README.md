# AESBuilder

AES 加密 SO 库一键构建工具，为 Android 项目快速生成独立的 AES 加密/解密 Native 库。

只需编辑一个 `config.json`，运行一条命令，即可自动生成包含签名校验、防调试、模拟器检测的加密 SO 库。

## 功能特性

- AES-128 加密/解密（CBC 模式 + Base64）
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
    "abi_filters": ["armeabi-v7a", "arm64-v8a"]
}
```

### 2. 运行构建

```bash
python build_so.py
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
```

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
| `jni_class_package` | JNI 类的包名 | 按目标项目调整 |
| `jni_class_name` | JNI 类名 | 按目标项目调整 |
| `method_encode` | 加密方法名 | 可自定义 |
| `method_decode` | 解密方法名 | 可自定义 |
| `method_check` | 签名校验方法名 | 可自定义 |
| `abi_filters` | 目标 CPU 架构 | 支持 armeabi-v7a、arm64-v8a |

> 详细使用说明请参阅 [使用说明.md](使用说明.md)

## License

MIT
