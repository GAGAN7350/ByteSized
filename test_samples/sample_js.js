/**
 * SiliconBob Test Sample: JavaScript / TypeScript
 * Demonstrates legacy scope hazard, loose equality type coercion, and debug log cleanup.
 */

var globalCounter = 0;

function evaluateUser(input, threshold) {
    console.log("Evaluating user with input: " + input);

    if (input == threshold) {
        var status = "active";
        return status;
    }

    if (input != null) {
        return "unverified";
    }

    return "unknown";
}
