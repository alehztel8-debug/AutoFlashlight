import os

os.makedirs("app/src/main/java/com/example/autoflashlight", exist_ok=True)

p = "".join(map(chr, [97, 110, 100, 114, 111, 105, 100]))
n = "".join(map(chr, [110, 97, 109, 101]))
a = f"{p}:{n}"
u = "".join(map(chr, [104, 116, 116, 112, 58, 47, 47, 115, 99, 104, 101, 109, 97, 115, 46, 97, 110, 100, 114, 111, 105, 100, 46, 99, 111, 109, 47, 97, 112, 107, 47, 114, 101, 115, 47, 97, 110, 100, 114, 111, 105, 100]))

manifest_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:{p}="{u}">
    <uses-permission {a}="{p}.permission.CAMERA" />
    <uses-permission {a}="{p}.permission.FLASHLIGHT" />
    <uses-permission {a}="{p}.permission.FOREGROUND_SERVICE" />
    <uses-permission {a}="{p}.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
    <uses-permission {a}="{p}.permission.POST_NOTIFICATIONS" />
    <uses-feature {a}="{p}.hardware.camera.flash" {p}:required="false" />
    <uses-feature {a}="{p}.hardware.sensor.light" {p}:required="false" />
    <application {p}:allowBackup="true" {p}:label="AutoFlashlight" {p}:theme="@style/Theme.Material3.DayNight.NoActionBar">
        <activity {a}=".MainActivity" {p}:exported="true">
            <intent-filter>
                <action {a}="{p}.intent.action.MAIN" />
                <category {a}="{p}.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <service {a}=".LightMonitorService" {p}:enabled="true" {p}:exported="false" {p}:foregroundServiceType="specialUse">
            <property {a}="{p}.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE" {p}:value="Monitoring ambient light" />
        </service>
    </application>
</manifest>
"""

service_kt = """package com.example.autoflashlight

import android.app.*
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.camera2.CameraManager
import android.os.Build
import android.os.IBinder
import android.widget.Toast
import androidx.core.app.NotificationCompat
import java.util.Calendar

class LightMonitorService : Service(), SensorEventListener {

    private lateinit var sensorManager: SensorManager
    private var lightSensor: Sensor? = null
    private lateinit var cameraManager: CameraManager
    private var cameraId: String? = null
    private var isTorchOn = false

    private var startHour = 18
    private var startMinute = 0
    private var endHour = 7
    private var endMinute = 0
    private var luxThreshold = 10f

    companion object {
        var currentLuxValue: Float = -1f
        var isRunning: Boolean = false
        var lastError: String = ""
    }

    override fun onCreate() {
        super.onCreate()
        try {
            sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
            lightSensor = sensorManager.getDefaultSensor(Sensor.TYPE_LIGHT)
            cameraManager = getSystemService(Context.CAMERA_SERVICE) as CameraManager
            cameraId = cameraManager.cameraIdList.firstOrNull()
            createNotificationChannel()
        } catch (e: Exception) {
            lastError = "Init error: ${e.message}"
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startHour = intent?.getIntExtra("START_HOUR", 18) ?: 18
        startMinute = intent?.getIntExtra("START_MIN", 0) ?: 0
        endHour = intent?.getIntExtra("END_HOUR", 7) ?: 7
        endMinute = intent?.getIntExtra("END_MIN", 0) ?: 0
        luxThreshold = intent?.getFloatExtra("LUX_THRESHOLD", 10f) ?: 10f

        val notification = NotificationCompat.Builder(this, "LIGHT_CHANNEL")
            .setContentTitle("AutoFlashlight Active")
            .setContentText("%02d:%02d - %02d:%02d (limit: ${luxThreshold.toInt()} lx)".format(startHour, startMinute, endHour, endMinute))
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
            } else {
                startForeground(1, notification)
            }
            isRunning = true
        } catch (e: Exception) {
            lastError = "Foreground error: ${e.message}"
            Toast.makeText(this, lastError, Toast.LENGTH_LONG).show()
            stopSelf()
            return START_NOT_STICKY
        }

        if (lightSensor != null) {
            sensorManager.registerListener(this, lightSensor, SensorManager.SENSOR_DELAY_NORMAL)
        } else {
            lastError = "Light sensor not found on this device"
            Toast.makeText(this, lastError, Toast.LENGTH_LONG).show()
        }

        return START_STICKY
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event?.sensor?.type == Sensor.TYPE_LIGHT) {
            val currentLux = event.values.firstOrNull() ?: return
            currentLuxValue = currentLux
            if (isWithinTimeWindow()) {
                if (currentLux <= luxThreshold && !isTorchOn) {
                    toggleTorch(true)
                } else if (currentLux > (luxThreshold + 15f) && isTorchOn) {
                    toggleTorch(false)
                }
            } else if (isTorchOn) {
                toggleTorch(false)
            }
        }
    }

    private fun isWithinTimeWindow(): Boolean {
        val now = Calendar.getInstance()
        val currentMins = now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE)
        val startMins = startHour * 60 + startMinute
        val endMins = endHour * 60 + endMinute

        return if (startMins <= endMins) {
            currentMins in startMins..endMins
        } else {
            currentMins >= startMins || currentMins <= endMins
        }
    }

    private fun toggleTorch(state: Boolean) {
        try {
            cameraId?.let {
                cameraManager.setTorchMode(it, state)
                isTorchOn = state
            }
        } catch (e: Exception) {
            lastError = "Flash error: ${e.message}"
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    override fun onDestroy() {
        isRunning = false
        try {
            sensorManager.unregisterListener(this)
            if (isTorchOn) toggleTorch(false)
        } catch (_: Exception) {}
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel("LIGHT_CHANNEL", "Light Monitoring", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(channel)
        }
    }
}
"""

activity_kt = """package com.example.autoflashlight

import android.Manifest
import android.app.TimePickerDialog
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity(), SensorEventListener {

    private var startHour = 18
    private var startMin = 0
    private var endHour = 7
    private var endMin = 0
    private var luxThreshold = 10f
    private lateinit var tvStatus: TextView
    private lateinit var btnToggle: Button
    private var sensorManager: SensorManager? = null
    private var lightSensor: Sensor? = null

    private val permLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) {
        if (hasPermissions()) {
            tvStatus.text = "Permissions granted! Tap Start"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(60, 100, 60, 60)
        }

        val btnStart = Button(this).apply { text = "Start time: 18:00" }
        val btnEnd = Button(this).apply { text = "End time: 07:00" }
        val tvLux = TextView(this).apply {
            text = "Darkness threshold: 10 lux"
            textSize = 16f
            setPadding(0, 40, 0, 16)
        }
        val seekLux = SeekBar(this).apply {
            max = 100
            progress = 10
        }
        btnToggle = Button(this).apply {
            text = if (LightMonitorService.isRunning) "Stop monitoring" else "Start monitoring"
        }
        tvStatus = TextView(this).apply {
            text = "Waiting to start..."
            textSize = 14f
            setPadding(0, 40, 0, 0)
        }

        layout.addView(btnStart)
        layout.addView(btnEnd)
        layout.addView(tvLux)
        layout.addView(seekLux)
        layout.addView(btnToggle)
        layout.addView(tvStatus)
        setContentView(layout)

        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        lightSensor = sensorManager?.getDefaultSensor(Sensor.TYPE_LIGHT)
        if (lightSensor == null) {
            tvStatus.text = "Warning: Light sensor (TYPE_LIGHT) not detected!"
        }

        btnStart.setOnClickListener {
            TimePickerDialog(this, { _, h, m ->
                startHour = h; startMin = m
                btnStart.text = "Start time: %02d:%02d".format(h, m)
}, startHour, startMin, true).show()
}
btnEnd.setOnClickListener {
TimePickerDialog(this, { _, h, m ->
endHour = h; endMin = m
btnEnd.text = "End time: %02d:%02d".format(h, m)
}, endHour, endMin, true).show()
}
seekLux.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
luxThreshold = progress.toFloat()
tvLux.text = "Darkness threshold: $progress lux"
}
override fun onStartTrackingTouch(seekBar: SeekBar?) {}
override fun onStopTrackingTouch(seekBar: SeekBar?) {}
})
btnToggle.setOnClickListener {
if (!hasPermissions()) {
requestPermissions()
return@setOnClickListener
}
toggleService()
}
requestPermissions()
}
private fun toggleService() {
val serviceIntent = Intent(this, LightMonitorService::class.java).apply {
putExtra("START_HOUR", startHour)
putExtra("START_MIN", startMin)
putExtra("END_HOUR", endHour)
putExtra("END_MIN", endMin)
putExtra("LUX_THRESHOLD", luxThreshold)
}
try {
if (!LightMonitorService.isRunning) {
ContextCompat.startForegroundService(this, serviceIntent)
btnToggle.text = "Stop monitoring"
tvStatus.text = "Service started"
} else {
stopService(serviceIntent)
btnToggle.text = "Start monitoring"
tvStatus.text = "Service stopped"
}
} catch (e: Exception) {
tvStatus.text = "Start error: ${e.message}"
}
}
private fun hasPermissions(): Boolean {
val cam = ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
val notif = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
} else true
return cam && notif
}
private fun requestPermissions() {
val perms = mutableListOf(Manifest.permission.CAMERA)
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
perms.add(Manifest.permission.POST_NOTIFICATIONS)
}
val needed = perms.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
if (needed.isNotEmpty()) {
permLauncher.launch(needed.toTypedArray())
}
}
override fun onResume() {
super.onResume()
lightSensor?.let {
sensorManager?.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
}
if (LightMonitorService.lastError.isNotEmpty()) {
tvStatus.text = LightMonitorService.lastError
}
}
override fun onPause() {
super.onPause()
sensorManager?.unregisterListener(this)
}
override fun onSensorChanged(event: SensorEvent?) {
if (event?.sensor?.type == Sensor.TYPE_LIGHT) {
val lux = event.values.firstOrNull() ?: 0f
val state = if (LightMonitorService.isRunning) "Running" else "Stopped"
tvStatus.text = "Current light: ${lux.toInt()} lux | Service: $state"
}
}
override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
}
"""
open("app/src/main/AndroidManifest.xml", "w").write(manifest_xml)
open("app/src/main/java/com/example/autoflashlight/LightMonitorService.kt", "w").write(service_kt)
open("app/src/main/java/com/example/autoflashlight/MainActivity.kt", "w").write(activity_kt)
