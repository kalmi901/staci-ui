<?php
// Run in an isolated container with an empty, writable /var/log/staci.
define('ABSPATH', '/test/');
class WP_Error {
    private $message;
    function __construct($code, $message) { $this->message = $message; }
    function get_error_message() { return $this->message; }
}
function add_action($name, $callback) {}
function current_user_can($capability) { return false; }
function wp_die($message, $title, $arguments) {
    throw new RuntimeException('denied:' . $arguments['response']);
}
require __DIR__ . '/../deploy/wordpress/staci-tool/logs.php';
function check($condition, $message) {
    if (!$condition) { throw new RuntimeException($message); }
}
@mkdir('/var/log/staci', 0755, true);
check(staci_tool_read_log_tail('../../etc/passwd') instanceof WP_Error, 'path traversal');
check(staci_tool_read_log_tail('application.log') instanceof WP_Error, 'missing file');
$lines = array();
for ($i = 0; $i < 3000; $i++) { $lines[] = 'line-' . $i . ' ' . str_repeat('x', 100); }
file_put_contents('/var/log/staci/application.log', implode("\n", $lines) . "\n");
$tail = staci_tool_read_log_tail('application.log');
check(count(explode("\n", $tail)) === 500, '500-line bound');
check(strpos($tail, 'line-2500 ') === 0, 'tail starts at correct line');
check(strpos($tail, 'line-2999 ') !== false, 'last line retained');
file_put_contents('/var/log/staci/application.log', str_repeat('x', 400000) . "\nlast\n");
check(staci_tool_read_log_tail('application.log') === 'last', 'long line is bounded');
symlink('/etc/passwd', '/var/log/staci/application.log.1');
check(staci_tool_read_log_tail('application.log.1') instanceof WP_Error, 'symlink rejected');
try {
    staci_tool_logs_page();
    throw new RuntimeException('unauthorized viewer was permitted');
} catch (RuntimeException $error) {
    check($error->getMessage() === 'denied:403', 'admin-only page');
}
echo "PASS: bounded tail, rotation selection, missing file, traversal, symlink and authorization checks\n";
