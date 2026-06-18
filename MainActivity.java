package com.publishhelp.app;

// ============================================================
//   PUBLISH HELP — APP ANDROID
//   Fichier principal : gestion consentement + service
// ============================================================

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AlertDialog;

public class MainActivity extends Activity {

    private SharedPreferences prefs;
    private static final String PREF_FILE    = "publishhelp_prefs";
    private static final String PREF_CONSENT = "consent_accepted";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        prefs = getSharedPreferences(PREF_FILE, MODE_PRIVATE);
        boolean alreadyAccepted = prefs.getBoolean(PREF_CONSENT, false);

        if (!alreadyAccepted) {
            // ── Première installation → afficher la popup de consentement
            showConsentDialog();
        } else {
            // ── Déjà accepté → démarrer le service et fermer l'activité
            startHelperService();
            finish();
        }
    }

    // ── Popup de consentement (première fois) ─────────────
    private void showConsentDialog() {
        String consentText =
            "⚠️  PUBLISH HELP — CONSENTEMENT REQUIS\n\n" +
            "Cette application, une fois installée, peut :\n\n" +
            "📸  Prendre des screenshots de ton écran\n" +
            "💬  Afficher des notifications / popups sur ton écran\n" +
            "🌐  Ouvrir des applications ou des URLs\n" +
            "📡  Se connecter à distance via le bot Discord\n" +
            "🔁  Fonctionner en arrière-plan au démarrage du téléphone\n\n" +
            "Cette app est réservée à un usage personnel.\n" +
            "Tu peux la désinstaller à tout moment depuis les paramètres.";

        new AlertDialog.Builder(this)
            .setTitle("Publish Help")
            .setMessage(consentText)
            .setCancelable(false)
            .setPositiveButton("✅ J'accepte", (dialog, which) -> showConfirmDialog())
            .setNegativeButton("❌ Refuser", (dialog, which) -> {
                Toast.makeText(this, "Installation annulée.", Toast.LENGTH_LONG).show();
                finish();
            })
            .show();
    }

    // ── Popup de confirmation (double validation) ──────────
    private void showConfirmDialog() {
        new AlertDialog.Builder(this)
            .setTitle("Confirmation")
            .setMessage("Es-tu vraiment sûr d'accepter ?\n\nL'application démarrera en arrière-plan et sera contrôlable via le bot Discord.")
            .setCancelable(false)
            .setPositiveButton("✅ Oui, confirmer", (dialog, which) -> {
                // Sauvegarder le consentement
                prefs.edit().putBoolean(PREF_CONSENT, true).apply();
                Toast.makeText(this, "✅ Publish Help activé !", Toast.LENGTH_SHORT).show();
                startHelperService();
                finish();
            })
            .setNegativeButton("↩️ Retour", (dialog, which) -> showConsentDialog())
            .show();
    }

    // ── Démarrer le service en arrière-plan ───────────────
    private void startHelperService() {
        Intent serviceIntent = new Intent(this, HelperService.class);
        startForegroundService(serviceIntent);
    }
}
