# AESBuilder

AES 加密 SO 库一键构建工具，为 Android 项目快速生成独立的 AES 加密/解密 Native 库。

以前每次为新项目生成 SO，需要手动改 6-7 个文件（C 源码、头文件、CMake、Gradle、Java 类），容易出错。现在只需编辑一个 `config.json`，运行一条命令，即可自动生成包含签名校验、防调试、模拟器检测的加密 SO 库。

## 功能特性

- AES-128 加密/解密（支持 ECB / CBC 模式 + Base64）
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

### 第一步：编辑配置

打开 `config.json`，按你的项目需求修改：

```json
{
    "package_name": "com.example.myapp",
    "signature_hash": 362543054,
    "aes_key": "1234567890abcdef",
    "interference_char": "N",
    "so_name": "MyEncrypt",
    "jni_class_package": "com.example.myapp.utils",
    "jni_class_name": "MyEncrypt",
    "method_encode": "my_encode",
    "method_decode": "my_decode",
    "method_check": "my_check",
    "encrypt_mode": "ECB",
    "sign_key": "&key=your_sign_key_here",
    "method_sign": "my_sign",
    "abi_filters": ["armeabi-v7a", "arm64-v8a"]
}
```

> `encrypt_mode` 可选，默认 `"ECB"`，可设为 `"CBC"` 使用 CBC 模式（随机 IV）。
> `sign_key` 和 `method_sign` 为可选字段。不需要 MD5 签名功能可以删除这两行，构建产物与之前完全一致。

### 第二步：运行构建

```bash
# 正式构建：生成目标项目的 SO 库
python build_so.py

# 测试模式：额外构建测试 APK
python build_so.py --test
```

### 第三步：取走产物

构建完成后，`output/` 目录结构如下：

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

将 SO 文件放到目标项目的 `jniLibs/` 目录，将 Java 文件复制到对应包路径下即可使用。

### 第四步：调用示例

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

---

## 配置字段说明

### 每个项目必须修改的字段

| 字段 | 说明 | 如何获取 |
|------|------|----------|
| `package_name` | 目标 APP 的 applicationId | 查看目标项目 `build.gradle.kts` 中的 `applicationId` |
| `signature_hash` | APK 签名的 hashCode，用于防二次打包 | 见下方「如何获取 signature_hash」 |
| `aes_key` | AES-128 密钥，**必须 16 个 ASCII 字符** | 自行定义，每个项目建议使用不同密钥 |

### 可选修改的字段（自定义命名）

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `so_name` | SO 库名称（最终文件为 `lib<so_name>.so`） | `"MyEncrypt"` |
| `jni_class_package` | Java/Kotlin JNI 类的包名，同时决定 SO 中 JNI 方法的注册路径 | `"com.example.myapp.utils"` |
| `jni_class_name` | JNI 类名 | `"MyEncrypt"` |
| `method_encode` | 加密方法名 | `"my_encode"` |
| `method_decode` | 解密方法名 | `"my_decode"` |
| `method_check` | 签名校验方法名 | `"my_check"` |

### 可选功能：加密模式

| 字段 | 说明 | 备注 |
|------|------|------|
| `encrypt_mode` | 加密模式，`"ECB"` 或 `"CBC"` | 可选，默认 `"ECB"`。CBC 模式使用随机 IV |

> 不填时默认使用 ECB 模式，与旧版 SO 保持兼容。

### 可选功能：MD5 签名

| 字段 | 说明 | 备注 |
|------|------|------|
| `sign_key` | 签名拼接密钥，输入字符串后追加此 key 再做 MD5 | 可选，不填则不生成 sign 功能 |
| `method_sign` | 签名方法名 | 可选，与 `sign_key` 必须同时配置 |

> 这两个字段要么同时填写，要么同时不填（或删除）。只填一个会报错。

### 一般不需要改的字段

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `interference_char` | 干扰字符，插入到 Base64 密钥前混淆，**单个字符** | `"N"` |
| `abi_filters` | 目标 CPU 架构列表 | `["armeabi-v7a", "arm64-v8a"]` |

---

## 如何获取 signature_hash

### 方法一：使用 app 测试模块（推荐）

本项目自带 `app` 模块，内置了 `SignatureUtil` 工具类。

1. 将 `config.json` 中的 `package_name` 改为目标项目的 applicationId
2. 编译运行 `app` 模块
3. 在 Logcat 中过滤 `AES_DEBUG`，即可看到：
   ```
   AES_DEBUG  D  签名哈希: -2043803321
   ```
4. 将该数值填入 `config.json` 的 `signature_hash`

> 注意：debug 签名和 release 签名的哈希值不同。正式发布时应使用 release keystore 签名后的哈希值。

### 方法二：在目标项目中调用工具类

将 `app` 模块中的 `SignatureUtil.kt` 复制到目标项目，调用：

```kotlin
val hash = SignatureUtil.getSignatureHashCode(context)
Log.d("AES_DEBUG", "签名哈希: $hash")
```

### 方法三：Java 代码获取

```java
// API 28+
PackageInfo info = context.getPackageManager()
        .getPackageInfo(context.getPackageName(), PackageManager.GET_SIGNING_CERTIFICATES);
int hash = info.signingInfo.getApkContentsSigners()[0].hashCode();

// API 28 以下
PackageInfo info = context.getPackageManager()
        .getPackageInfo(context.getPackageName(), PackageManager.GET_SIGNATURES);
int hash = info.signatures[0].hashCode();

Log.d("AES_DEBUG", "签名哈希: " + hash);
```

---

## 为其他项目生成 SO 的完整流程

以「智能AI」APP 为例：

**1. 获取目标项目信息**

| 信息 | 值 |
|------|-----|
| applicationId | `com.deepchat.bot` |
| 签名哈希 | `-625644214`（通过上述方法获取） |
| 想要的密钥 | `9ce7ee6ff027eb0f` |

**2. 编辑 config.json**

```json
{
    "package_name": "com.deepchat.bot",
    "signature_hash": -625644214,
    "aes_key": "9ce7ee6ff027eb0f",
    "interference_char": "N",
    "so_name": "ZJEncrypt",
    "jni_class_package": "com.zyhd.library.net.encrypt",
    "jni_class_name": "ZJEncrypt",
    "method_encode": "ZJ_encode",
    "method_decode": "ZJ_decode",
    "method_check": "ZJ_check",
    "sign_key": "&key=your_sign_key_here",
    "method_sign": "ZJ_sign",
    "abi_filters": ["armeabi-v7a", "arm64-v8a"]
}
```

**3. 运行构建**

```bash
python build_so.py
```

**4. 集成到目标项目**

将 `output/` 中的文件复制到目标项目：

```
目标项目/
└── app/src/main/
    ├── jniLibs/
    │   ├── armeabi-v7a/
    │   │   └── libZJEncrypt.so
    │   └── arm64-v8a/
    │       └── libZJEncrypt.so
    └── java/com/zyhd/network_api/utils/
        └── ZJEncrypt.java
```

**5. 在目标项目中调用**

```kotlin
// 加密
val encrypted = ZJEncrypt.ZJ_encode(context, "hello world")

// 解密
val decrypted = ZJEncrypt.ZJ_decode(context, encrypted)

// 签名校验（返回 1 表示通过）
val result = ZJEncrypt.ZJ_check(context)

// MD5 签名（需配置 sign_key 和 method_sign）
val signed = ZJEncrypt.ZJ_sign(context, "data_to_sign")
```

---

## app 测试模块

项目自带 `app` 模块，用于测试加解密功能：

- 输入明文，点击「加密」调用 native 加密
- 点击「解密」对加密结果还原
- 点击「签名」对输入做 MD5 签名（仅在配置了 sign_key/method_sign 时显示）
- 自动执行签名校验并显示结果
- 启动时打印签名哈希到 Logcat（标签 `AES_DEBUG`）

### 使用测试模式

要让测试 app 通过签名校验，需将 `config.json` 中的 `package_name` 和 `signature_hash` 设为测试 app 的值：

1. 将 `package_name` 设为 `"com.example.myapp"`（测试 app 的 applicationId）
2. 运行测试 app，在 Logcat 过滤 `AES_DEBUG` 获取签名哈希
3. 将哈希值填入 `signature_hash`
4. 运行 `python build_so.py --test`

`--test` 模式会额外执行 `app:assembleDebug` 构建测试 APK。正式构建时改回目标项目的值，运行 `python build_so.py` 即可。

> 在 Android Studio 中直接点击 Run 也可以，`app` 模块的 `preBuild` 会自动调用 `build_so.py --generate-only` 重新生成源文件。

---

## 项目结构

```
AESBuilder/
├── config.json              ← 唯一需要编辑的配置文件
├── build_so.py              ← 构建脚本，python build_so.py 运行
├── templates/               ← 模板文件（脚本自动替换占位符）
│   ├── JNIEncrypt.c.tmpl
│   ├── checksignature.h.tmpl
│   ├── CMakeLists.txt.tmpl
│   ├── build.gradle.kts.tmpl
│   ├── JniEncrypt.java.tmpl
│   └── MainActivity.kt.tmpl
├── lib_module/              ← Android Library 模块（native 源码）
│   └── src/main/cpp/        ← C 源码（静态文件 + 由脚本生成的文件）
├── app/                     ← 测试模块（加解密测试 + 签名哈希获取）
│   └── src/main/kotlin/
│       └── com/example/myapp/
│           ├── MainActivity.kt
│           └── SignatureUtil.kt
├── output/                  ← 构建产物输出
├── build.gradle.kts         ← Gradle 根配置
├── settings.gradle.kts
├── gradle.properties
├── local.properties         ← SDK 路径（按需修改）
└── gradlew / gradlew.bat
```

---

## 常见问题

**Q: 签名校验返回 -1**
A: 包名不匹配。检查 `config.json` 的 `package_name` 是否与目标 APP 的 `applicationId` 一致。

**Q: 签名校验返回 -2**
A: 签名哈希不匹配。确认 `signature_hash` 是用正确的 keystore 签名后获取的值。debug 和 release 签名哈希不同。

**Q: 加解密返回 UNSIGNATURE**
A: 签名校验未通过。native 层的 encode/decode 函数会先校验签名，校验失败直接返回 `UNSIGNATURE`，不会执行加解密。

**Q: 构建报错 "Unsupported class file major version"**
A: Gradle 版本与 JDK 不兼容。本项目使用 Gradle 8.4+ / AGP 8.x，需要 JDK 17 或 21。

**Q: 构建报错找不到 SDK 或 NDK**
A: 检查 `local.properties` 中的 `sdk.dir` 路径是否正确，确保 SDK 下安装了 NDK 和 CMake。

**Q: 想只生成某一个架构的 SO**
A: 修改 `config.json` 中的 `abi_filters`，例如只保留 `["arm64-v8a"]`。

**Q: aes_key 可以用中文吗**
A: 不可以，必须是 16 个 ASCII 字符（字母、数字、符号均可）。

**Q: sign_key 和 method_sign 是什么**
A: 可选的 MD5 签名功能。配置后 SO 会包含一个 sign 方法，将输入字符串拼接 `sign_key` 后计算 MD5，返回 32 位十六进制摘要。不需要可以不填或删除这两个字段。

**Q: 只填了 sign_key 没填 method_sign（或反过来），报错了**
A: 这两个字段必须同时配置或同时不填，不能只填一个。

## License

MIT
