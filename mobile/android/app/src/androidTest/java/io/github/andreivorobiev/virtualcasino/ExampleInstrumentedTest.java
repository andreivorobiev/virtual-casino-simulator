package io.github.andreivorobiev.virtualcasino;

import static org.junit.Assert.assertEquals;

import android.content.Context;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Instrumented identity test for the generated Casino Simulator Android application.
 */
@RunWith(AndroidJUnit4.class)
public class ExampleInstrumentedTest {

    @Test
    public void usesCasinoSimulatorAppContext() {
        // Resolve the application context supplied by the installed debug test target.
        Context appContext = InstrumentationRegistry.getInstrumentation().getTargetContext();

        // Verify the installed application id matches the shared Capacitor configuration.
        assertEquals("io.github.andreivorobiev.virtualcasino", appContext.getPackageName());
    }
}
