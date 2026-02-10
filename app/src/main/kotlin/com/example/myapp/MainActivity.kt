package com.example.myapp

import android.os.Bundle
import android.util.Log
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.example.myapp.utils.MyEncrypt
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText

class MainActivity : AppCompatActivity() {

    private var lastEncrypted = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        val etInput = findViewById<TextInputEditText>(R.id.et_input)
        val tvEncryptResult = findViewById<TextView>(R.id.tv_encrypt_result)
        val tvDecryptResult = findViewById<TextView>(R.id.tv_decrypt_result)
        val tvCheckResult = findViewById<TextView>(R.id.tv_check_result)
        val btnEncrypt = findViewById<MaterialButton>(R.id.btn_encrypt)
        val btnDecrypt = findViewById<MaterialButton>(R.id.btn_decrypt)

        // 打印当前签名哈希
        val signatureHash = SignatureUtil.getSignatureHashCode(this)
        Log.d("AES_DEBUG", "签名哈希: $signatureHash")

        // 签名校验
        try {
            val checkResult = MyEncrypt.my_check(this)
            tvCheckResult.text = if (checkResult == 1) "通过 (1)" else "未通过 ($checkResult)"
        } catch (e: Exception) {
            tvCheckResult.text = "校验异常: %s".format(e.message)
        }

        // 加密
        btnEncrypt.setOnClickListener {
            val input = etInput.text?.toString()?.trim().orEmpty()
            if (input.isEmpty()) {
                Toast.makeText(this, "请输入明文", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            try {
                lastEncrypted = MyEncrypt.my_encode(this, input)
                tvEncryptResult.text = lastEncrypted
            } catch (e: Exception) {
                tvCheckResult.text = "加密失败: %s".format(e.message)
            }
        }

        // 解密
        btnDecrypt.setOnClickListener {
            if (lastEncrypted.isEmpty()) {
                Toast.makeText(this, "请先加密", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            try {
                val decrypted = MyEncrypt.my_decode(this, lastEncrypted)
                tvDecryptResult.text = decrypted
            } catch (e: Exception) {
                tvCheckResult.text = "解密失败: %s".format(e.message)
            }
        }
    }
}
