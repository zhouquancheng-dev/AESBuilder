package com.example.myapp

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build

object SignatureUtil {

    /**
     * 获取当前应用的签名哈希值
     * 用于填入 config.json 的 signature_hash 字段
     */
    fun getSignatureHashCode(context: Context): Int? {
        return try {
            val packageName = context.packageName
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                val packageInfo = context.packageManager
                    .getPackageInfo(packageName, PackageManager.GET_SIGNING_CERTIFICATES)
                packageInfo.signingInfo?.apkContentsSigners?.firstOrNull()?.hashCode()
            } else {
                @Suppress("DEPRECATION")
                val packageInfo = context.packageManager
                    .getPackageInfo(packageName, PackageManager.GET_SIGNATURES)
                @Suppress("DEPRECATION")
                packageInfo.signatures?.firstOrNull()?.hashCode()
            }
        } catch (_: Exception) {
            null
        }
    }
}
