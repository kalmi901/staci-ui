<?php
/** Read-only viewer for the application's bounded, rotated log files. */
defined('ABSPATH') || exit;
require_once __DIR__ . '/run-log-page.php';

function staci_tool_log_names() {
    return array('application.log', 'application.log.1', 'application.log.2',
        'application.log.3', 'application.log.4', 'application.log.5');
}

function staci_tool_read_log_tail($name) {
    if (!in_array($name, staci_tool_log_names(), true)) {
        return new WP_Error('invalid_log', 'Érvénytelen naplófájl.');
    }
    $directory = '/var/log/staci';
    $path = $directory . '/' . $name;
    $resolved = realpath($path);
    if (is_link($path) || !$resolved || dirname($resolved) !== realpath($directory)
        || !is_file($resolved) || !is_readable($resolved)) {
        return new WP_Error('missing_log', 'A naplófájl nem érhető el.');
    }
    // Never load a complete rotated log into PHP memory. Rotation may happen
    // between selection and opening: a missing file is a harmless refresh case.
    $handle = @fopen($resolved, 'rb');
    if (!$handle) {
        return new WP_Error('unavailable_log', 'A naplófájl nem nyitható meg. Frissítse az oldalt.');
    }
    $stat = fstat($handle);
    $offset = max(0, $stat['size'] - 262144);
    if (fseek($handle, $offset) !== 0) {
        fclose($handle);
        return new WP_Error('unavailable_log', 'A napló nem olvasható.');
    }
    if ($offset > 0) {
        // Drop a possibly partial first line, with a bounded read even for long lines.
        fgets($handle, 262145);
    }
    $text = stream_get_contents($handle, 262144);
    fclose($handle);
    if ($text === false) {
        return new WP_Error('unavailable_log', 'A napló nem olvasható.');
    }
    $lines = explode("\n", rtrim($text, "\n"));
    return implode("\n", array_slice($lines, -500));
}

function staci_tool_logs_page() {
    if (!current_user_can('manage_options')) {
        wp_die('Nincs jogosultságod a napló megtekintéséhez.', '', array('response' => 403));
    }
    if (staci_run_query('view') !== 'raw') {
        staci_run_page();
        return;
    }
    nocache_headers();
    $name = isset($_GET['log']) && is_string($_GET['log'])
        ? sanitize_text_field(wp_unslash($_GET['log'])) : 'application.log';
    $content = staci_tool_read_log_tail($name);
    echo '<div class="wrap"><h1>STACI napló</h1>';
    echo '<p><a class="button" href="' . esc_url(admin_url('tools.php?page=staci-tool-logs')) . '">Futáslista</a></p>';
    echo '<p>Alkalmazásnapló. Időzóna: UTC (Z).</p>';
    echo '<form method="get" action="' . esc_url(admin_url('tools.php')) . '">';
    echo '<input type="hidden" name="page" value="staci-tool-logs"><input type="hidden" name="view" value="raw">';
    echo '<label for="staci-log-file">Naplófájl: </label>';
    echo '<select id="staci-log-file" name="log">';
    foreach (staci_tool_log_names() as $option) {
        $label = $option === 'application.log' ? $option . ' — aktuális' : $option;
        echo '<option value="' . esc_attr($option) . '"' . selected($name, $option, false) . '>'
            . esc_html($label) . '</option>';
    }
    echo '</select> ';
    submit_button('Frissítés', 'secondary', 'submit', false);
    echo '</form><p>Legfeljebb 500 sor a fájl utolsó 256 KiB-jából. '
        . 'Az .1 a legutóbbi archív fájl.</p>';
    if (is_wp_error($content)) {
        echo '<div class="notice notice-info"><p>' . esc_html($content->get_error_message()) . '</p></div>';
    } else {
        echo '<pre style="background:#fff;border:1px solid #c3c4c7;padding:16px;max-height:65vh;'
            . 'overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;">'
            . esc_html($content !== '' ? $content : 'Nincs naplóbejegyzés.') . '</pre>';
    }
    echo '</div>';
}

add_action('admin_menu', function () {
    add_management_page('STACI napló', 'STACI napló', 'manage_options',
        'staci-tool-logs', 'staci_tool_logs_page');
});
