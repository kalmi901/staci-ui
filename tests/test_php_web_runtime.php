<?php
// Run inside the disposable Apache container; its localhost has no public port.
define('STACI_PHP_SECURITY_TEST', true);
require __DIR__ . '/../deploy/wordpress/check-php-security.php';

$context = stream_context_create(array('http' => array('timeout' => 1)));
$body = false;
for ($attempt = 0; $attempt < 50; $attempt++) {
    $body = @file_get_contents('http://127.0.0.1/', false, $context);
    if ($body !== false) { break; }
    usleep(100000);
}
$result = $body !== false ? json_decode($body, true) : null;
if (!is_array($result)
    || ($result['sapi'] ?? null) !== 'apache2handler'
    || ($result['version'] ?? null) !== PHP_VERSION
    || staci_php_security_status($result['version'])['status'] !== 'patched'
    || ($result['session_loaded'] ?? null) !== true
    || !in_array($result['upload_progress'] ?? null, array('', '0'), true)) {
    throw new RuntimeException('Apache must serve patched PHP with session upload progress disabled.');
}
echo 'PASS: Apache PHP ' . $result['version'] . " is patched; session upload progress disabled\n";
