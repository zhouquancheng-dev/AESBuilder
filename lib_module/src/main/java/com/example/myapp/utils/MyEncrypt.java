package com.example.myapp.utils;

public class MyEncrypt {

    static {
        System.loadLibrary("MyEncrypt");
    }

    /**
     * AES加密
     */
    public static native String my_encode(Object context, String str);

    /**
     * AES解密
     */
    public static native String my_decode(Object context, String str);

    /**
     * 签名校验
     */
    public static native int my_check(Object context);

}
