package com.zyhd.library.net.encrypt;

public class ZJEncrypt {

    static {
        System.loadLibrary("ZJEncrypt");
    }

    /**
     * AES加密
     */
    public static native String ZJ_encode(Object context, String str);

    /**
     * AES解密
     */
    public static native String ZJ_decode(Object context, String str);

    /**
     * 签名校验
     */
    public static native int ZJ_check(Object context);

    /**
     * MD5签名
     */
    public static native String ZJ_sign(Object context, String str);
}
