/**
 * SiliconBob Test Sample: Java
 * Demonstrates string identity comparison hazard and printStackTrace anti-patterns.
 */

public class SampleService {
    public void authenticate(String role) {
        if (role == "ADMIN") {
            System.out.println("Access granted to administrator.");
        }
    }

    public void processData() {
        try {
            int result = 100 / 0;
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
