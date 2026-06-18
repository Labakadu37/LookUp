package com.publishhelp.app;

// ============================================================
//   PUBLISH HELP — SERVICE EN ARRIÈRE-PLAN
//   Maintient la connexion Socket.IO et exécute les commandes
// ============================================================

import android.app.*;
import android.content.*;
import android.graphics.Bitmap;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.media.ImageReader;
import android.media.projection.*;
import android.net.Uri;
import android.os.*;
import android.util.Base64;
import android.util.DisplayMetrics;
import android.view.*;
import android.widget.*;
import androidx.core.app.NotificationCompat;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;

// Dépendances Socket.IO (à ajouter dans build.gradle)
// implementation 'io.socket:socket.io-client:2.1.0'
import io.socket.client.IO;
import io.socket.client.Socket;
import io.socket.emitter.Emitter;

public class HelperService extends Service {

    // ── Configuration — À MODIFIER avec ton IP et ta clé ──
    private static final String SERVER_URL  = "http://TON_IP_SERVEUR:3000";
    private static final String SECRET_KEY  = "change_cette_cle_secrete_en_quelque_chose_de_long_et_aleatoire";
    private static final String DEVICE_NAME = "Mon Android";   // Nom affiché dans .ip
    private static final String PLATFORM    = "android";

    private static final String CHANNEL_ID  = "publish_help_channel";
    private static final int    NOTIF_ID    = 1;

    private Socket socket;
    private WindowManager windowManager;

    // ── Démarrage du service ───────────────────────────────
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        createNotificationChannel();
        startForeground(NOTIF_ID, buildNotification());
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        connectSocket();
        return START_STICKY; // Redémarre automatiquement si tué
    }

    // ── Connexion Socket.IO ───────────────────────────────
    private void connectSocket() {
        try {
            IO.Options opts = new IO.Options();
            opts.auth = new JSONObject()
                .put("secret", SECRET_KEY)
                .put("platform", PLATFORM)
                .put("deviceName", DEVICE_NAME);
            opts.reconnection = true;
            opts.reconnectionDelay = 3000;

            socket = IO.socket(SERVER_URL, opts);

            socket.on(Socket.EVENT_CONNECT, args ->
                android.util.Log.d("PublishHelp", "✅ Connecté au serveur")
            );

            socket.on(Socket.EVENT_DISCONNECT, args ->
                android.util.Log.d("PublishHelp", "❌ Déconnecté")
            );

            // ── Réception des commandes du bot ─────────────
            socket.on("command", args -> {
                try {
                    JSONObject data = (JSONObject) args[0];
                    String command  = data.getString("command");
                    handleCommand(command, data);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });

            socket.connect();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // ── Dispatcher des commandes ───────────────────────────
    private void handleCommand(String command, JSONObject data) throws Exception {
        switch (command) {
            case "screenshot":
                String channelId = data.getString("channelId");
                requestScreenshot(channelId);
                break;

            case "show_popup":
                String text = data.getString("text");
                showPopup(text);
                break;

            case "open_url":
                String url = data.getString("url");
                openUrl(url);
                break;
        }
    }

    // ── Commande : Screenshot ─────────────────────────────
    // Note : nécessite MediaProjection (permission demandée à l'user)
    // Pour une implémentation simple, on envoie un message d'info
    private void requestScreenshot(String channelId) {
        // TODO : implémenter MediaProjection pour le vrai screenshot
        // Pour l'instant on notifie le bot que la feature nécessite une action manuelle
        try {
            JSONObject result = new JSONObject();
            result.put("channelId", channelId);
            result.put("type", "error");
            result.put("content", "Screenshot Android nécessite une autorisation MediaProjection. Lance l'app pour l'autoriser.");
            socket.emit("command_result", result);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // ── Commande : Popup message ──────────────────────────
    private void showPopup(String text) {
        new Handler(Looper.getMainLooper()).post(() -> {
            // Crée une fenêtre flottante visible par-dessus tout
            View popupView = LayoutInflater.from(this).inflate(R.layout.popup_message, null);
            TextView tv    = popupView.findViewById(R.id.popup_text);
            Button   btn   = popupView.findViewById(R.id.popup_close);
            tv.setText(text);

            WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
            );
            params.gravity = Gravity.CENTER;

            windowManager.addView(popupView, params);
            btn.setOnClickListener(v -> windowManager.removeView(popupView));
        });
    }

    // ── Commande : Ouvrir une URL ─────────────────────────
    private void openUrl(String url) {
        new Handler(Looper.getMainLooper()).post(() -> {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        });
    }

    // ── Notification persistante (obligatoire pour foreground) ──
    private Notification buildNotification() {
        Intent stopIntent = new Intent(this, StopReceiver.class);
        PendingIntent stopPi = PendingIntent.getBroadcast(this, 0, stopIntent,
            PendingIntent.FLAG_IMMUTABLE);

        return new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Publish Help")
            .setContentText("Connecté et en attente de commandes...")
            .setSmallIcon(android.R.drawable.ic_menu_send)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .addAction(android.R.drawable.ic_delete, "Arrêter", stopPi)
            .build();
    }

    private void createNotificationChannel() {
        NotificationChannel channel = new NotificationChannel(
            CHANNEL_ID, "Publish Help", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Service de contrôle à distance");
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(channel);
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onDestroy() {
        if (socket != null) socket.disconnect();
        super.onDestroy();
    }
}
