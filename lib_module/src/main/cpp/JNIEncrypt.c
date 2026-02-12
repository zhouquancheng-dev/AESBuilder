#include <jni.h>
#include "aes.h"
#include "checksignature.h"
#include "check_emulator.h"
#include <string.h>
#include <stdio.h>
#include <sys/ptrace.h>
#include "md5.h"
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)

#define CBC 1
#define ECB 1


// 获取数组的大小
# define NELEM(x) ((int) (sizeof(x) / sizeof((x)[0])))
// 指定要注册的类，对应完整的java类名
#define JNIREG_CLASS "com/zyhd/library/net/encrypt/ZJEncrypt"

const char *UNSIGNATURE = "UNSIGNATURE";

jstring charToJstring(JNIEnv *envPtr, const char *src) {
    JNIEnv env = *envPtr;

    jsize len = strlen(src);
    jclass clsstring = env->FindClass(envPtr, "java/lang/String");
    jstring strencode = env->NewStringUTF(envPtr, "UTF-8");
    jmethodID mid = env->GetMethodID(envPtr, clsstring, "<init>",
                                     "([BLjava/lang/String;)V");
    jbyteArray barr = env->NewByteArray(envPtr, len);
    env->SetByteArrayRegion(envPtr, barr, 0, len, (jbyte *) src);

    return (jstring) env->NewObject(envPtr, clsstring, mid, barr, strencode);
}

//__attribute__((section (".mytext")))
unsigned char *getKey() {
    int n = 0;
    char s[26];
    s[n++] = 'N';
    s[n++] = 'M';
    s[n++] = 'T';
    s[n++] = 'l';
    s[n++] = 'h';
    s[n++] = 'N';
    s[n++] = 'j';
    s[n++] = 'J';
    s[n++] = 'j';
    s[n++] = 'O';
    s[n++] = 'W';
    s[n++] = 'I';
    s[n++] = '5';
    s[n++] = 'N';
    s[n++] = 'D';
    s[n++] = 'g';
    s[n++] = '1';
    s[n++] = 'O';
    s[n++] = 'D';
    s[n++] = 'V';
    s[n++] = 'm';
    s[n++] = 'Z';
    s[n++] = 'g';
    s[n++] = '=';
    s[n++] = '=';
    s[n] = '\0';
    char *encode_str = s + 1;
    return b64_decode(encode_str, strlen(encode_str));

}

JNIEXPORT jstring JNICALL encode(JNIEnv *env, jobject instance, jobject context, jstring str_) {

    //先进行apk被 二次打包的校验
    if (check_signature(env, instance, context) != 1 || check_is_emulator(env) != 1) {
        const char *str = UNSIGNATURE;
        return charToJstring(env,str);
    }

    uint8_t *AES_KEY = (uint8_t *) getKey();
    const char *in = (*env)->GetStringUTFChars(env, str_, JNI_FALSE);
    char *baseResult = AES_128_CBC_PKCS5Padding_Encrypt(in, AES_KEY);
    (*env)->ReleaseStringUTFChars(env, str_, in);
    jstring  result = (*env)->NewStringUTF(env, baseResult);
    free(baseResult);
    free(AES_KEY);
    return result;
}


JNIEXPORT jstring JNICALL decode(JNIEnv *env, jobject instance, jobject context, jstring str_) {

    //先进行apk被 二次打包的校验
    if (check_signature(env, instance, context) != 1|| check_is_emulator(env) != 1) {
        const char *str = UNSIGNATURE;
        return charToJstring(env,str);
    }

    uint8_t *AES_KEY = (uint8_t *) getKey();
    const char *str = (*env)->GetStringUTFChars(env, str_, JNI_FALSE);
    char *desResult = AES_128_CBC_PKCS5Padding_Decrypt(str, AES_KEY);
    (*env)->ReleaseStringUTFChars(env, str_, str);
    jstring result = charToJstring(env,desResult);
    free(desResult);
    free(AES_KEY);
    return result;
}


/**
 * if rerurn 1 ,is check pass.
 */
JNIEXPORT jint JNICALL
check_jni(JNIEnv *env, jobject instance, jobject con) {
    return check_signature(env, instance, con);
}



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
    hex_result[32] = '\0';

    return (*env)->NewStringUTF(env, hex_result);
}

// Java和JNI函数的绑定表
static JNINativeMethod method_table[] = {
        {"ZJ_check", "(Ljava/lang/Object;)I",                                    (void *) check_jni},
        {"ZJ_decode",         "(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/String;", (void *) decode},
        {"ZJ_encode",         "(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/String;", (void *) encode},
        {"ZJ_sign",         "(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/String;", (void *) sign},
};

// 注册native方法到java中
static int registerNativeMethods(JNIEnv *env, const char *className,
                                 JNINativeMethod *gMethods, int numMethods) {
    jclass clazz;
    clazz = (*env)->FindClass(env, className);
    if (clazz == NULL) {
        return JNI_FALSE;
    }
    if ((*env)->RegisterNatives(env, clazz, gMethods, numMethods) < 0) {
        return JNI_FALSE;
    }

    return JNI_TRUE;
}

int register_ndk_load(JNIEnv *env) {
    // 调用注册方法
    return registerNativeMethods(env, JNIREG_CLASS,
                                 method_table, NELEM(method_table));
}

JNIEXPORT jint JNI_OnLoad(JavaVM *vm, void *reserved) {

    ptrace(PTRACE_TRACEME, 0, 0, 0);//反调试

    JNIEnv *env = NULL;
    jint result = -1;

    if ((*vm)->GetEnv(vm, (void **) &env, JNI_VERSION_1_4) != JNI_OK) {
        return result;
    }

    register_ndk_load(env);

// 返回jni的版本
    return JNI_VERSION_1_4;
}
