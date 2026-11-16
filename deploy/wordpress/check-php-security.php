<?php
/** Verify upstream PHP releases fixing CVE-2026-109618 and CVE-2026-109619. */
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}

function staci_php_security_status(string $version): array {
    $minimums = array(
        '8.2' => '8.2.35',
        '8.3' => '8.3.36',
        '8.4' => '8.4.27',
        '8.5' => '8.5.12',
    );
    // Official WordPress images use upstream stable versions. Vendor backports
    // and development releases require a separate assessment; do not guess.
    if (!preg_match('/\A(8\.[2-5])\.(0|[1-9][0-9]*)\z/', $version, $matches)) {
        return array('status' => 'unsupported', 'minimum' => null);
    }
    $minimum = $minimums[$matches[1]];
    return array(
        'status' => version_compare($version, $minimum, '>=') ? 'patched' : 'unpatched',
        'minimum' => $minimum,
    );
}

// Only the standalone regression test opts out of checking the current runtime.
if (!defined('STACI_PHP_SECURITY_TEST')) {
    $result = staci_php_security_status(PHP_VERSION);
    $patched = $result['status'] === 'patched';
    $detail = $result['minimum'] !== null
        ? 'minimum ' . $result['minimum']
        : 'requires a supported stable upstream PHP 8.2, 8.3, 8.4 or 8.5 release';
    fwrite($patched ? STDOUT : STDERR,
        'PHP ' . PHP_VERSION . ': ' . $result['status'] . ' (' . $detail . ").\n");
    exit($patched ? 0 : 1);
}
