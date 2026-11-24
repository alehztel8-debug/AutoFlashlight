package com.example.autoflashlight

import android.Manifest
import android.app.TimePickerDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.SeekBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private var startHour = 18
    private var startMin = 0
    private var endHour = 7
    private var endMin = 0
    private var luxThreshold = 10f
    private var isServiceRunning = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        requestPermissions()

        val btnStart = findViewById<Button>(R.id.btnStartTime)
        val btnEnd = findViewById<Button>(R.id.btnEndTime)
        val tvLux = findViewById<TextView>(R.id.tvLuxLabel)
        val seekLux = findViewById<SeekBar>(R.id.seekLux)
        val btnToggle = findViewById<Button>(R.id.btnToggleService)

        btnStart.setOnClickListener {
            TimePickerDialog(this, { _, h, m ->
                startHour = h; startMin = m
                btnStart.text = "Время начала: %02d:%02d".format(h, m)
            }, startHour, startMin, true).show()
        }

        btnEnd.setOnClickListener {
            TimePickerDialog(this, { _, h, m ->
                endHour = h; endMin = m
                btnEnd.text = "Время окончания: %02d:%02d".format(h, m)
            }, endHour, endMin, true).show()
        }

        seekLux.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                luxThreshold = progress.toFloat()
                tvLux.text = "Порог срабатывания: $progress люкс"
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        btnToggle.setOnClickListener {
            val serviceIntent = Intent(this, LightMonitorService::class.java).apply {
                putExtra("START_HOUR", startHour)
                putExtra("START_MIN", startMin)
                putExtra("END_HOUR", endHour)
                putExtra("END_MIN", endMin)
                putExtra("LUX_THRESHOLD", luxThreshold)
            }

            if (!isServiceRunning) {
                ContextCompat.startForegroundService(this, serviceIntent)
                btnToggle.text = "Остановить мониторинг"
                isServiceRunning = true
            } else {
                stopService(serviceIntent)
                btnToggle.text = "Запустить мониторинг"
                isServiceRunning = false
            }
        }
    }

    private fun requestPermissions() {
        val perms = mutableListOf(Manifest.permission.CAMERA)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        val needed = perms.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), 101)
        }
    }
}
