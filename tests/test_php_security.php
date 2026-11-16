<?php
/** Standalone checks; no WordPress, network or production volumes required. */
define('STACI_PHP_SECURITY_TEST', true);
require __DIR__ . '/../deploy/wordpress/check-php-security.php';

function check_php_security($version, $expected) {
    $actual = staci_php_security_status($version)['status'];
    if ($actual !== $expected) {
        throw new RuntimeException($version . ': expected ' . $expected . ', got ' . $actual);
    }
}

foreach (array(
    '8.2.34' => 'unpatched', '8.2.35' => 'patched', '8.2.36' => 'patched',
    '8.3.35' => 'unpatched', '8.3.36' => 'patched', '8.3.37' => 'patched',
    '8.4.26' => 'unpatched', '8.4.27' => 'patched', '8.4.28' => 'patched',
    '8.5.11' => 'unpatched', '8.5.12' => 'patched', '8.5.13' => 'patched',
    '8.2.0' => 'unpatched', '8.3.9' => 'unpatched', '8.4.9' => 'unpatched',
    '8.5.9' => 'unpatched', '8.3.100' => 'patched',
) as $version => $expected) {
    check_php_security($version, $expected);
}

foreach (array(
    '7.4.99', '8.0.99', '8.1.99', '8.6.0', '9.0.0',
    '8.3.36-dev', '8.3.36RC1', '8.3.36alpha1', '8.3.36beta1',
    '8.3.36+vendor', '8.3.36-1ubuntu1', '8.3.36.1',
    '', '8.3', '8.03.36', '8.3.036', ' 8.3.36', "8.3.36\n",
) as $version) {
    check_php_security($version, 'unsupported');
}

echo "PASS: PHP patch boundaries, numeric versions, unsupported branches and prereleases\n";
