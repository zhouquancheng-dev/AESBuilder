buildscript {
    dependencies {
        classpath("com.android.tools.build:gradle:8.11.2")
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.2.0")
    }
    repositories {
        google()
        mavenCentral()
        maven { url = uri("https://jitpack.io") }
    }
}

plugins {
    id("com.android.application") version "8.11.2" apply false
    id("com.android.library") version "8.11.2" apply false
    id("org.jetbrains.kotlin.android") version "2.2.0" apply false
    id("com.google.devtools.ksp") version "2.2.0-2.0.2" apply false
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}

extra["minSdk"] = "26"
extra["targetSdk"] = "35"
extra["compileSdk"] = "35"
extra["versionCode"] = "1"
extra["versionName"] = "1.0.0"
extra["applicationId"] = "com.example.myapp"
extra["otherName"] = "AES加解密测试"