//
// Created by wei on 16-12-4.
//

#include <string.h>
#include <android/log.h>
#include <jni.h>
#include "checksignature.h"


jint check_signature(JNIEnv *env, jobject thiz, jobject context) {
    //Context的类
    jclass context_clazz = (*env)->GetObjectClass(env, context);
    if (context_clazz == NULL) return -3;

    // 得到 getPackageManager 方法的 ID
    jmethodID methodID_getPackageManager = (*env)->GetMethodID(env,
                                                               context_clazz, "getPackageManager",
                                                               "()Landroid/content/pm/PackageManager;");
    if (methodID_getPackageManager == NULL) return -3;

    // 获得PackageManager对象
    jobject packageManager = (*env)->CallObjectMethod(env, context,
                                                      methodID_getPackageManager);
    if (packageManager == NULL) return -3;

//	// 获得 PackageManager 类
    jclass pm_clazz = (*env)->GetObjectClass(env, packageManager);
    if (pm_clazz == NULL) return -3;

    // 得到 getPackageInfo 方法的 ID
    jmethodID methodID_pm = (*env)->GetMethodID(env, pm_clazz, "getPackageInfo",
                                                "(Ljava/lang/String;I)Landroid/content/pm/PackageInfo;");
    if (methodID_pm == NULL) return -3;

//
//	// 得到 getPackageName 方法的 ID
    jmethodID methodID_pack = (*env)->GetMethodID(env, context_clazz,
                                                  "getPackageName", "()Ljava/lang/String;");
    if (methodID_pack == NULL) return -3;

    // 获得当前应用的包名
    jstring application_package = (*env)->CallObjectMethod(env, context,
                                                           methodID_pack);
    if (application_package == NULL) return -3;

    const char *package_name = (*env)->GetStringUTFChars(env,
                                                         application_package, 0);
    if (package_name == NULL) return -3;

    // 获得PackageInfo
    jobject packageInfo = (*env)->CallObjectMethod(env, packageManager,
                                                   methodID_pm, application_package, 64);
    if (packageInfo == NULL) {
        (*env)->ReleaseStringUTFChars(env, application_package, package_name);
        return -3;
    }

    jclass packageinfo_clazz = (*env)->GetObjectClass(env, packageInfo);
    if (packageinfo_clazz == NULL) {
        (*env)->ReleaseStringUTFChars(env, application_package, package_name);
        return -3;
    }

    jfieldID fieldID_signatures = (*env)->GetFieldID(env, packageinfo_clazz,
                                                     "signatures", "[Landroid/content/pm/Signature;");
    if (fieldID_signatures == NULL) {
        (*env)->ReleaseStringUTFChars(env, application_package, package_name);
        return -3;
    }

    jobjectArray signature_arr = (jobjectArray) (*env)->GetObjectField(env,
                                                                       packageInfo, fieldID_signatures);
    if (signature_arr == NULL) {
        (*env)->ReleaseStringUTFChars(env, application_package, package_name);
        return -3;
    }

    //Signature数组中取出第一个元素
    jobject signature = (*env)->GetObjectArrayElement(env, signature_arr, 0);
    if (signature == NULL) {
        (*env)->ReleaseStringUTFChars(env, application_package, package_name);
        return -3;
    }

    //读signature的hashcode
    jclass signature_clazz = (*env)->GetObjectClass(env, signature);
    if (signature_clazz == NULL) {
        (*env)->ReleaseStringUTFChars(env, application_package, package_name);
        return -3;
    }

    jmethodID methodID_hashcode = (*env)->GetMethodID(env, signature_clazz,
                                                      "hashCode", "()I");
    if (methodID_hashcode == NULL) {
        (*env)->ReleaseStringUTFChars(env, application_package, package_name);
        return -3;
    }

    jint hashCode = (*env)->CallIntMethod(env, signature, methodID_hashcode);

    jint result;
    if (strcmp(package_name, app_packageName) != 0) {
        result = -1;
    } else if (hashCode != app_signature_hash_code) {
        result = -2;
    } else {
        result = 1;
    }

    (*env)->ReleaseStringUTFChars(env, application_package, package_name);
    return result;
}
