<?php
// Disposable PHP container only: synthetic logs and run files, no production mounts.
define('ABSPATH', '/test/');
function add_action($name, $callback) {}
function current_user_can($cap) {
    return PHP_SAPI === 'cli' ? ($GLOBALS['authorized'] ?? true) : (($_SERVER['HTTP_X_TEST_ROLE'] ?? '') === 'admin');
}
function wp_die($message, $title, $args) {
    if (PHP_SAPI === 'cli') { throw new RuntimeException('denied:' . $args['response']); }
    http_response_code($args['response']); exit($message);
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
if (PHP_SAPI !== 'cli') { staci_run_download_file(); }
function check($condition, $message) { if (!$condition) { throw new RuntimeException($message); } }
function denied($code) {
    try { staci_run_prepare_file_download(); throw new RuntimeException('access permitted'); }
    catch (RuntimeException $e) { check($e->getMessage() === 'denied:' . $code, $e->getMessage() . ' expected ' . $code); }
}
function nonce($id, $file = 'inp') { return hash('sha256', 'staci_download_run_file_' . $id . '_' . $file); }
function select_file($id, $file = 'inp') {
    $_GET = array('execution' => $id, 'file' => $file, '_wpnonce' => nonce($id, $file));
}
function event_line($id, $event, $data) {
    return '2026-11-04 10:00:00,123Z | INFO     | src.run_logging | execution_id=' . $id
        . ' | user_id=7 user="researcher" | STACI_RUN '
        . json_encode(array_merge(array('schema' => 1, 'execution_id' => $id, 'event' => $event), $data)) . "\n";
}
function run_log($id, $rid, $bytes) {
    return event_line($id, 'started', array('run_type' => 'hydraulic', 'model_id' => '123456abcdef',
        'filename' => 'original.inp', 'settings' => array('backend' => 'staci', 'override_enabled' => true)))
        . event_line($id, 'allocated', array('run_id' => $rid))
        . event_line($id, 'prepared', array('run_id' => $rid, 'input_sha256' => hash('sha256', $bytes)));
}
function read_download() {
    $download = staci_run_prepare_file_download();
    $body = stream_get_contents($download['stream']); fclose($download['stream']);
    return array($body, $download);
}
$id = str_repeat('a', 32); $other = str_repeat('b', 32); $missing = str_repeat('c', 32);
$rid = 'abcdef123456'; $rid2 = 'fedcba654321';
$root = '/var/lib/staci-data/runs'; $directory = $root . '/hydraulic/' . $rid;
$path = $directory . '/input.inp'; $json_path = $directory . '/results.meta.json';
@mkdir($directory, 0755, true); @mkdir($root . '/hydraulic/' . $rid2, 0755, true);
@mkdir('/var/log/staci', 0755, true); @mkdir('/var/lib/staci-data/uploads/123456abcdef', 0755, true);
$bytes = "; prepared with overridden duration\r\n[TIMES]\r\nDURATION 2\r\n\x00\xff[END]\r\n";
$second_bytes = "; another run of the same upload\n[TIMES]\nDURATION 3\n";
$metadata = "{\n  \"simulation\": {\"duration_seconds\": 7200}\n}\n";
file_put_contents($path, $bytes); file_put_contents($json_path, $metadata);
file_put_contents($root . '/hydraulic/' . $rid2 . '/input.inp', $second_bytes);
$original = '/var/lib/staci-data/uploads/123456abcdef/original.inp';
file_put_contents($original, "; uploaded original\n[TIMES]\nDURATION 1\n");
$log_a = run_log($id, $rid, $bytes); $log_b = run_log($other, $rid2, $second_bytes);
file_put_contents('/var/log/staci/application.log.1', $log_a);
file_put_contents('/var/log/staci/application.log', $log_b);
$limited = false; $runs = staci_run_index(staci_run_records('/var/log/staci', $limited), $limited);
$run = $runs[$id];
check(staci_run_file_path($run, 'inp') === $path, 'exact prepared input from explicit run');
check(staci_run_file_path($run, 'parameters') === $json_path, 'STACI solver metadata');
foreach (array('../etc', strtoupper($rid), str_repeat('a', 13), array($rid)) as $bad) {
    check(staci_run_file_path(array_merge($run, array('run_id' => $bad)), 'inp') === false, 'invalid run ID');
}
foreach (array('../hydraulic', 'unknown', array('hydraulic')) as $bad) {
    check(staci_run_file_path(array_merge($run, array('type' => $bad)), 'inp') === false, 'invalid run type');
}
check(staci_run_file_path($run, '../input.inp') === false, 'file allowlist');
check(staci_run_file_path(array_merge($run, array('legacy' => true)), 'inp') === false, 'legacy records not guessed');
check(staci_run_file_path(array_merge($run, array('started' => false)), 'inp') === false, 'missing start not guessed');
$bad = $run; unset($bad['events']['allocated'], $bad['events']['prepared']);
check(staci_run_file_path($bad, 'inp') === false, 'finish ID alone insufficient');
$bad = $run; $bad['events']['prepared']['run_id'] = $rid2;
check(staci_run_file_path($bad, 'inp') === false, 'conflicting run IDs rejected');
$bad = $run; $bad['events']['finished']['run_id'] = $rid2;
check(staci_run_file_path($bad, 'inp') === false, 'conflicting finish rejected');

// Existing per-type files, including XML, are returned without conversion.
foreach (array('partition' => array('model.inp', 'staci_split_settings.xml'),
    'flushing' => array('model.inp', 'flushing_config.json')) as $type => $names) {
    $sample = $run; $sample['type'] = $type;
    $dir = $root . '/' . $type . '/' . $rid; mkdir($dir, 0755, true);
    foreach ($names as $name) { file_put_contents($dir . '/' . $name, 'stored ' . $name); }
    check(staci_run_file_path($sample, 'inp') === $dir . '/' . $names[0], $type . ' input');
    check(staci_run_file_path($sample, 'parameters') === $dir . '/' . $names[1], $type . ' parameters');
}
$wntr = $run; $wntr['events']['started']['settings']['backend'] = 'wntr';
file_put_contents($directory . '/run.json', '{"backend":"wntr","files":{}}');
check(staci_run_file_path($wntr, 'parameters') === $directory . '/run.json', 'WNTR manifest explicitly selected');
check(staci_run_file_specs($wntr)['parameters']['label'] === 'Futásleíró (JSON)', 'WNTR manifest not claimed as complete parameters');

$authorized = false; $_SERVER['REQUEST_METHOD'] = 'GET'; $_GET = array(); denied(403);
$authorized = true; $_SERVER['REQUEST_METHOD'] = 'POST'; denied(405);
$_SERVER['REQUEST_METHOD'] = 'GET'; select_file($id);
unset($_GET['_wpnonce']); denied(403);
$_GET['_wpnonce'] = array('invalid'); denied(403);
select_file($id); $_GET['execution'] = array($id); denied(403);
select_file($id); $_GET['_wpnonce'] = nonce($other); denied(403);
select_file($id); $_GET['file'] = 'parameters'; denied(403);
select_file($id); $_GET['file'] = '../../etc/passwd'; denied(403);
select_file($id); $_GET['file'] = array('inp'); denied(403);
select_file($id);
$_GET += array('path' => '/etc/passwd', 'run_id' => $rid2, 'type' => 'partition', 'filename' => 'original.inp');
list($body, $download) = read_download();
check($body === $bytes && $body !== file_get_contents($original), 'prepared bytes, not original upload');
check($download['filename'] === $rid . '-input.inp' && $download['size'] === strlen($bytes), 'run-specific attachment name');
select_file($other); list($body) = read_download(); check($body === $second_bytes, 'same-model attempts stay separate');
select_file($id, 'parameters'); list($body, $download) = read_download();
check($body === $metadata && $download['filename'] === $rid . '-results.meta.json', 'byte-exact parameter attachment');
unlink($original); select_file($id); list($body) = read_download(); check($body === $bytes, 'no dependency on original upload');
file_put_contents($path, 'changed after run'); denied(409); file_put_contents($path, $bytes);
rename($json_path, $json_path . '.saved'); select_file($id, 'parameters'); denied(404);
select_file($id); list($body) = read_download(); check($body === $bytes, 'missing metadata does not hide available input');
rename($json_path . '.saved', $json_path);
foreach (array($path, $json_path, $directory, $root . '/hydraulic', $root) as $target) {
    rename($target, $target . '.saved'); symlink($target . '.saved', $target);
    select_file($id, $target === $json_path ? 'parameters' : 'inp'); denied(404);
    unlink($target); rename($target . '.saved', $target);
}
select_file($id); rename($path, $path . '.saved'); mkdir($path); denied(404); rmdir($path); rename($path . '.saved', $path);
chmod($path, 0000); if (posix_geteuid() !== 0) { denied(404); } chmod($path, 0644);
select_file($missing); denied(404);
unlink('/var/log/staci/application.log.1'); select_file($id); denied(404);
file_put_contents('/var/log/staci/application.log.1', $log_a);

// Real HTTP responses: two attachments, precise bytes, status and cache policy.
$server = proc_open(array(PHP_BINARY, '-S', '127.0.0.1:18083', __FILE__),
    array(0 => array('pipe', 'r'), 1 => array('file', '/tmp/staci-download-http.log', 'a'),
        2 => array('file', '/tmp/staci-download-http.log', 'a')), $pipes);
check(is_resource($server), 'HTTP fixture starts');
try {
    $ready = false;
    for ($i = 0; $i < 50; $i++) {
        $socket = @fsockopen('127.0.0.1', 18083, $errno, $error, 0.1);
        if ($socket) { fclose($socket); $ready = true; break; } usleep(100000);
    }
    check($ready, 'HTTP fixture ready');
    function request_file($id, $file, $role = 'admin', $token = null, $method = 'GET') {
        $context = stream_context_create(array('http' => array('method' => $method,
            'header' => 'X-Test-Role: ' . $role, 'ignore_errors' => true, 'timeout' => 5)));
        $query = http_build_query(array('execution' => $id, 'file' => $file, '_wpnonce' => $token ?? nonce($id, $file)));
        $body = file_get_contents('http://127.0.0.1:18083/?' . $query, false, $context);
        return array($http_response_header, $body);
    }
    foreach (array('inp' => array($bytes, 'input.inp'), 'parameters' => array($metadata, 'results.meta.json')) as $file => $expected) {
        list($headers, $body) = request_file($id, $file);
        check(str_contains($headers[0], '200 OK') && $body === $expected[0], 'HTTP exact ' . $file);
        $headers = implode("\n", $headers);
        check(str_contains($headers, 'Content-Type: application/octet-stream'), 'binary content type');
        check(str_contains($headers, 'Content-Disposition: attachment; filename="' . $rid . '-' . $expected[1] . '"'), 'attachment filename');
        check(str_contains($headers, 'Content-Length: ' . strlen($expected[0])), 'content length');
        check(str_contains($headers, 'X-Content-Type-Options: nosniff') && str_contains($headers, 'private, no-store'), 'no execution or shared caching');
        foreach (array('', 'subscriber') as $role) {
            list($headers) = request_file($id, $file, $role); check(str_contains($headers[0], '403'), 'HTTP admin-only');
        }
    }
    list($headers) = request_file($id, 'parameters', 'admin', nonce($id, 'inp')); check(str_contains($headers[0], '403'), 'HTTP file-bound nonce');
    list($headers) = request_file($id, 'inp', 'admin', 'expired'); check(str_contains($headers[0], '403'), 'HTTP expired link');
    list($headers) = request_file($id, 'inp', 'admin', null, 'POST'); check(str_contains($headers[0], '405'), 'HTTP GET only');
    file_put_contents($path, 'modified');
    list($headers) = request_file($id, 'inp'); check(str_contains($headers[0], '409'), 'HTTP checksum mismatch');
    unlink($path);
    list($headers, $body) = request_file($id, 'inp');
    check(str_contains($headers[0], '404') && !str_contains($body, '/var/lib/'), 'HTTP missing input without path disclosure');
} finally { proc_terminate($server); proc_close($server); }
echo "PASS: prepared INP, per-run metadata, overrides, same-model attempts, checksum, authorization, nonce scope, missing files, traversal, symlinks and HTTP attachments\n";
