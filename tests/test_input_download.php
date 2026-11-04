<?php
// Run in a disposable PHP 8 container; never mount production log/data volumes.
// In HTTP mode the same fixture exercises the actual streaming handler.
define('ABSPATH', '/test/');
function add_action($name, $callback) {}
function current_user_can($cap) {
    return PHP_SAPI === 'cli' ? ($GLOBALS['authorized'] ?? true) : (($_SERVER['HTTP_X_TEST_ROLE'] ?? '') === 'admin');
}
function wp_die($message, $title, $args) {
    if (PHP_SAPI === 'cli') { throw new RuntimeException('denied:' . $args['response']); }
    http_response_code($args['response']);
    exit($message);
}
function nocache_headers() { if (PHP_SAPI !== 'cli') { header('Cache-Control: no-cache'); } }
function wp_unslash($s) { return $s; }
function wp_verify_nonce($nonce, $action) { return hash_equals(hash('sha256', $action), $nonce); }
function admin_url($s) { return '/wp-admin/' . $s; }
function add_query_arg($args, $base) { return $base . '?' . http_build_query($args); }
function wp_nonce_url($url, $action) { return $url . '&_wpnonce=' . hash('sha256', $action); }
function staci_tool_log_names() { return array('application.log', 'application.log.1', 'application.log.2', 'application.log.3', 'application.log.4', 'application.log.5'); }
require __DIR__ . '/../deploy/wordpress/staci-tool/run-log-data.php';
require __DIR__ . '/../deploy/wordpress/staci-tool/input-download.php';
if (PHP_SAPI !== 'cli') { staci_run_download_upload(); }
function check($condition, $message) { if (!$condition) { throw new RuntimeException($message); } }
function denied($code) {
    try { staci_run_prepare_upload_download(); throw new RuntimeException('access permitted'); }
    catch (RuntimeException $e) { check($e->getMessage() === 'denied:' . $code, $e->getMessage() . ' expected ' . $code); }
}
function event_line($id, $model, $filename) {
    return '2026-10-15 10:00:00,123Z | INFO     | src.run_logging | execution_id=' . $id
        . ' | user_id=7 user="researcher" | STACI_RUN '
        . json_encode(array('schema' => 1, 'execution_id' => $id, 'event' => 'started',
            'run_type' => 'hydraulic', 'model_id' => $model, 'filename' => $filename)) . "\n";
}
$id = str_repeat('a', 32); $other = str_repeat('b', 32);
$model = '123456abcdef'; $filename = 'network_original.inp';
$root = '/var/lib/staci-data/uploads';
$directory = $root . '/' . $model; $path = $directory . '/' . $filename;
@mkdir($directory, 0755, true); @mkdir('/var/log/staci', 0755, true);
$bytes = "; original input\r\n[JUNCTIONS]\r\n\x00\xff[END]\r\n";
file_put_contents($path, $bytes);
file_put_contents('/var/log/staci/application.log.1', event_line($id, $model, $filename));
$run = array('started' => true, 'legacy' => false, 'model_id' => $model, 'filename' => $filename);
check(staci_run_upload_path($run) === $path, 'exact stored upload');
foreach (array('../network.inp', '..', '.', '/etc/passwd', 'nested/file.inp', 'nested\\file.inp', "bad\r\nheader.inp", 'a".inp', "a\0.inp") as $bad) {
    check(staci_run_upload_path(array_merge($run, array('filename' => $bad))) === false, 'unsafe filename');
}
foreach (array('../etc', strtoupper($model), str_repeat('a', 13)) as $bad) {
    check(staci_run_upload_path(array_merge($run, array('model_id' => $bad))) === false, 'unsafe model');
}
check(staci_run_upload_path(array_merge($run, array('started' => false))) === false, 'no guessed run association');
check(staci_run_upload_path(array_merge($run, array('legacy' => true))) === false, 'no ambiguous legacy association');
$authorized = false; $_SERVER['REQUEST_METHOD'] = 'GET'; $_GET = array(); denied(403);
$authorized = true; $_SERVER['REQUEST_METHOD'] = 'POST'; denied(405);
$_SERVER['REQUEST_METHOD'] = 'GET';
$_GET = array('execution' => $id); denied(403);
$_GET['_wpnonce'] = 'expired'; denied(403);
$_GET['_wpnonce'] = array('invalid'); denied(403);
$_GET = array('execution' => array($id), '_wpnonce' => 'invalid'); denied(403);
$_GET = array('execution' => $id, '_wpnonce' => hash('sha256', 'staci_download_upload_' . $other)); denied(403);
$_GET['_wpnonce'] = hash('sha256', 'staci_download_upload_' . $id);
// Caller-supplied paths/model IDs must have no influence on the selected file.
$_GET['path'] = '/etc/passwd'; $_GET['filename'] = 'passwd'; $_GET['model_id'] = $other;
$download = staci_run_prepare_upload_download();
check(stream_get_contents($download['stream']) === $bytes, 'byte-exact original upload from rotated log');
check($download['filename'] === $filename && $download['size'] === strlen($bytes), 'attachment metadata');
fclose($download['stream']);
rename($path, $path . '.saved');
symlink($path . '.saved', $path); denied(404); unlink($path);
symlink('/etc/passwd', $path); denied(404); unlink($path);
mkdir($path); denied(404); rmdir($path);
rename($path . '.saved', $path);
rename($directory, $directory . '.saved');
symlink($directory . '.saved', $directory); denied(404); unlink($directory);
rename($directory . '.saved', $directory);
rename($root, $root . '.saved'); symlink($root . '.saved', $root); denied(404); unlink($root); rename($root . '.saved', $root);
chmod($path, 0000);
// CI runs as www-data, so this also exercises actual filesystem permissions.
if (posix_geteuid() !== 0) { denied(404); }
chmod($path, 0644);
rename($path, $path . '.saved'); denied(404); rename($path . '.saved', $path);
$_GET = array('execution' => $other, '_wpnonce' => hash('sha256', 'staci_download_upload_' . $other)); denied(404);
unlink('/var/log/staci/application.log.1');
$_GET = array('execution' => $id, '_wpnonce' => hash('sha256', 'staci_download_upload_' . $id)); denied(404);
file_put_contents('/var/log/staci/application.log', event_line($id, $model, $filename));

// Check real HTTP status, headers, cache policy and binary response bytes.
$server = proc_open(array(PHP_BINARY, '-S', '127.0.0.1:18083', __FILE__),
    array(0 => array('pipe', 'r'), 1 => array('file', '/tmp/staci-download-http.log', 'a'),
        2 => array('file', '/tmp/staci-download-http.log', 'a')), $pipes);
check(is_resource($server), 'HTTP fixture starts');
try {
    $ready = false;
    for ($i = 0; $i < 50; $i++) {
        $socket = @fsockopen('127.0.0.1', 18083, $errno, $error, 0.1);
        if ($socket) { fclose($socket); $ready = true; break; }
        usleep(100000);
    }
    check($ready, 'HTTP fixture ready');
    function request_file($id, $role, $nonce, $method = 'GET') {
        $context = stream_context_create(array('http' => array('method' => $method,
            'header' => 'X-Test-Role: ' . $role, 'ignore_errors' => true, 'timeout' => 5)));
        $body = file_get_contents('http://127.0.0.1:18083/?execution=' . $id . '&_wpnonce=' . $nonce, false, $context);
        return array($http_response_header, $body);
    }
    $nonce = hash('sha256', 'staci_download_upload_' . $id);
    list($headers, $body) = request_file($id, 'admin', $nonce);
    check(str_contains($headers[0], '200 OK') && $body === $bytes, 'HTTP exact binary download');
    $headers = implode("\n", $headers);
    check(str_contains($headers, 'Content-Type: application/octet-stream'), 'binary content type');
    check(str_contains($headers, 'Content-Disposition: attachment; filename="' . $filename . '"'), 'attachment filename');
    check(str_contains($headers, 'Content-Length: ' . strlen($bytes)), 'content length');
    check(str_contains($headers, 'X-Content-Type-Options: nosniff') && str_contains($headers, 'private, no-store'), 'no execution or shared caching');
    foreach (array('', 'subscriber') as $role) {
        list($headers, $body) = request_file($id, $role, $nonce);
        check(str_contains($headers[0], '403') && $body !== $bytes, 'HTTP admin-only');
    }
    list($headers, $body) = request_file($id, 'admin', 'expired');
    check(str_contains($headers[0], '403'), 'HTTP invalid nonce');
    list($headers, $body) = request_file($id, 'admin', $nonce, 'POST');
    check(str_contains($headers[0], '405'), 'HTTP GET only');
    unlink($path);
    list($headers, $body) = request_file($id, 'admin', $nonce);
    check(str_contains($headers[0], '404') && !str_contains($body, '/var/lib/'), 'HTTP missing upload without path disclosure');
} finally { proc_terminate($server); proc_close($server); }
echo "PASS: original bytes, rotated logs, authorization, nonce scope, missing files, traversal, symlinks, permissions and HTTP attachment\n";
