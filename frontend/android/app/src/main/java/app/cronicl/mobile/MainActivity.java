package app.cronicl.mobile;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override public void onCreate(android.os.Bundle savedInstanceState) {
        registerPlugin(CroniclNativePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
