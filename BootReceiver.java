package com.publishhelp.app;

// ============================================================
//   PUBLISH HELP — DÉMARRAGE AUTOMATIQUE AU BOOT
//   L'app se relance quand le téléphone redémarre
// ============================================================

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            // Démarrer le service en arrière-plan automatiquement
            Intent serviceIntent = new Intent(context, HelperService.class);
            context.startForegroundService(serviceIntent);
        }
    }
}
