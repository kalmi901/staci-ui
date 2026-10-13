<?php
// Run only in an isolated PHP container with an empty /var/log/staci.
define('ABSPATH', '/test/');
$authorized = true;
function current_user_can($cap) { global $authorized; return $authorized; }
function wp_die($message, $title, $args) { throw new RuntimeException('denied:' . $args['response']); }
function nocache_headers() {}
function sanitize_text_field($s) { return strip_tags($s); }
function wp_unslash($s) { return $s; }
function admin_url($s) { return '/wp-admin/' . $s; }
function esc_html($s) { return htmlspecialchars((string) $s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function esc_attr($s) { return esc_html($s); }
function esc_textarea($s) { return esc_html($s); }
function esc_url($s) { return esc_html($s); }
function remove_accents($s) { return $s; }
function selected($a, $b, $echo) { return $a === $b ? ' selected' : ''; }
function submit_button($text, ...$args) { echo '<button>' . esc_html($text) . '</button>'; }
function add_query_arg($args, $base) { return $base . '?' . http_build_query($args); }
function staci_tool_log_names() { return array('application.log', 'application.log.1', 'application.log.2', 'application.log.3', 'application.log.4', 'application.log.5'); }
require __DIR__ . '/../deploy/wordpress/staci-tool/run-log-page.php';
function check($condition, $message) { if (!$condition) { throw new RuntimeException($message); } }
function line($id, $message, $logger = 'src.run_logging') {
    return '2026-10-07 12:00:00,123Z | INFO     | ' . $logger . ' | execution_id=' . $id
        . ' | user_id=7 user=' . json_encode('Árvíz | " <script>') . ' | ' . $message . "\n";
}
function event_line($id, $event, $data = array()) {
    return line($id, 'STACI_RUN ' . json_encode(array_merge(array('schema' => 1, 'execution_id' => $id, 'event' => $event), $data)));
}
$a = str_repeat('a', 32); $b = str_repeat('b', 32); $c = str_repeat('c', 32);
@mkdir('/var/log/staci', 0755, true);
file_put_contents('/var/log/staci/application.log.1',
    event_line($a, 'started', array('run_type' => 'hydraulic', 'model_id' => '123456abcdef', 'filename' => '</textarea><script>alert(1)</script>.inp'))
    . event_line($b, 'started', array('run_type' => 'hydraulic', 'model_id' => '123456abcdef', 'filename' => 'same.inp')));
file_put_contents('/var/log/staci/application.log',
    line($a, 'Calculation failed', 'workflow') . "Traceback\nValueError: isolated failure\n"
    . event_line($b, 'prepared', array('run_id' => 'abcdef123456', 'input_sha256' => str_repeat('f', 64)))
    . event_line($b, 'finished', array('status' => 'completed_with_warnings'))
    . event_line($a, 'finished', array('status' => 'failed'))
    . event_line($c, 'finished', array('status' => 'completed'))
    . "2026-10-07 11:00:00,123Z | INFO     | workflow | user_id=7 user=\"old\" | Hydraulic simulation started: model_id=123456abcdef, backend=wntr\n"
    . "2026-10-07 11:00:01,123Z | INFO     | workflow | user_id=7 user=\"old\" | Hydraulic simulation finished: model_id=123456abcdef, run_id=abcdef123456, backend=wntr\n");
$limited = false;
$runs = staci_run_index(staci_run_records('/var/log/staci', $limited), $limited);
check(count($runs) === 5, 'new attempts and unpaired legacy events');
check($runs[$a]['status'] === 'failed', 'failed status');
check(str_contains($runs[$a]['raw'], 'ValueError: isolated failure'), 'traceback retained');
check(!str_contains($runs[$b]['raw'], 'isolated failure'), 'concurrent attempts do not mix');
check($runs[$b]['status'] === 'completed_with_warnings', 'warning status');
check($runs[$c]['status'] === 'incomplete', 'missing start is not complete history');
check($runs[$a]['user'] === 'Árvíz | " <script>', 'quoted unicode identity');
check(staci_run_user_label(array('user_id' => '-', 'user' => '-')) === 'Nem rögzített', 'missing user is explicit');
check(staci_run_user_label($runs[$a]) === 'Árvíz | " <script> (ID: 7)', 'known user attribution preserved');
check(staci_run_local_time('2026-10-07 12:00:00,123Z') === '2026-10-07 14:00:00 CEST', 'summer time');
check(staci_run_local_time('2026-01-07 12:00:00,123Z') === '2026-01-07 13:00:00 CET', 'winter time');
$_GET = array('execution' => $a);
ob_start(); staci_run_page(); $html = ob_get_clean();
check(!str_contains($html, '<script>alert(1)'), 'log content must not execute');
check(str_contains($html, '&lt;script&gt;alert(1)'), 'escaped content displayed');
check(str_contains($html, 'staci-copy-summary'), 'copy control');
$_GET = array('status' => 'failed', 'from' => '2026-10-07', 'to' => '2026-10-07');
ob_start(); staci_run_page(); $filtered = ob_get_clean();
check(str_contains($filtered, 'Futáslista (1)'), 'status and date filter');
$authorized = false;
try { staci_run_page(); throw new RuntimeException('authorization bypass'); }
catch (RuntimeException $e) { check($e->getMessage() === 'denied:403', 'admin-only'); }
// A symlink must never become an input to the index.
symlink('/etc/passwd', '/var/log/staci/application.log.2');
$limited = false;
check(count(staci_run_index(staci_run_records('/var/log/staci', $limited), $limited)) === 5, 'symlink ignored');
// Retention is bounded, including per-run details.
$records = array();
for ($i = 0; $i < 510; $i++) {
    $record = staci_run_header(event_line(sprintf('%032x', $i + 1), 'started', array('run_type' => 'partition')));
    $record['raw'] = str_repeat('x', 26000);
    $records[] = $record;
}
$limited = false; $bounded = staci_run_index($records, $limited);
check(count($bounded) === 500 && $limited, '500-run bound');
check(strlen(reset($bounded)['raw']) === 24576 && reset($bounded)['truncated'], 'per-run detail bound');
echo "PASS: correlation, rotation, legacy uncertainty, traceback, timezone, escaping, filtering, authorization and bounds\n";
