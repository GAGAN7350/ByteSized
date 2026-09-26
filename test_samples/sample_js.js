// =============================================================================
// JavaScript Test Sample: Legacy Scope and Type Coercion Hazards
// =============================================================================

// 1. Bug: var leaks into outer scope
var userToken = "auth_secret_xyz";
var requestCount = 42;

// 2. Bug: Loose equality type coercion bug
function verifyAuth(inputCode) {
    if (inputCode == 0) {
        return "Access Granted";
    }
    return "Access Denied";
}
