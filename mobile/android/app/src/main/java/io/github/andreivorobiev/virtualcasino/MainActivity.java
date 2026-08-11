package io.github.andreivorobiev.virtualcasino;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(CasinoSecureTransportPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
