<?php
// CI-only fixture, copied into a disposable Apache container with no network.
header('Content-Type: application/json');
echo json_encode(array(
    'version' => PHP_VERSION,
    'sapi' => PHP_SAPI,
    'session_loaded' => extension_loaded('session'),
    'upload_progress' => ini_get('session.upload_progress.enabled'),
));
