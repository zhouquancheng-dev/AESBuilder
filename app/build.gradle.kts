import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
}

android {
    namespace = rootProject.extra["applicationId"].toString()
    compileSdk = rootProject.extra["compileSdk"].toString().toInt()

    defaultConfig {
        applicationId = rootProject.extra["applicationId"].toString()
        minSdk = rootProject.extra["minSdk"].toString().toInt()
        targetSdk = rootProject.extra["targetSdk"].toString().toInt()
        versionCode = rootProject.extra["versionCode"].toString().toInt()
        versionName = rootProject.extra["versionName"].toString()
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
            isShrinkResources = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlin {
        compilerOptions {
            jvmTarget.set(JvmTarget.JVM_17)
            javaParameters.set(true)
        }
    }

    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    implementation(project(":lib_module"))

    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("com.google.android.material:material:1.13.0")
}
