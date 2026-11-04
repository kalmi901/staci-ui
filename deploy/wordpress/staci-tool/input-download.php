<?php
/** Download original uploads referenced by retained run logs, administrators only. */
defined('ABSPATH') || exit;

function staci_run_upload_path($run) {
    $model = $run['model_id'] ?? '';
    $name = $run['filename'] ?? '';
    if (!empty($run['legacy']) || empty($run['started'])
        || !is_string($model) || !preg_match('/\A[a-f0-9]{12}\z/', $model)
        || !is_string($name) || strlen($name) > 255 || !preg_match('/\A[A-Za-z0-9_.-]+\z/', $name)
        || $name === '.' || $name === '..') {
        return false;
    }
    // These paths come only from the indexed log, never from URL path parameters.
    // Reject symlinks at every level, including ones pointing inside the volume.
    $root = '/var/lib/staci-data/uploads';
    $directory = $root . '/' . $model;
    $path = $directory . '/' . $name;
    clearstatcache();
    if (is_link($root) || realpath($root) !== $root
        || is_link($directory) || realpath($directory) !== $directory
        || is_link($path) || realpath($path) !== $path
        || !is_file($path) || !is_readable($path)) {
        return false;
    }
    return $path;
}

function staci_run_upload_url($id) {
    return wp_nonce_url(add_query_arg(array('action' => 'staci_download_upload',
        'execution' => $id), admin_url('admin-post.php')), 'staci_download_upload_' . $id);
}

function staci_run_prepare_upload_download() {
    if (!current_user_can('manage_options')) {
        wp_die('Nincs jogosultságod a fájl letöltéséhez.', '', array('response' => 403));
    }
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
        wp_die('Nem támogatott kérés.', '', array('response' => 405));
    }
    $id = isset($_GET['execution']) && is_string($_GET['execution']) ? wp_unslash($_GET['execution']) : '';
    $nonce = isset($_GET['_wpnonce']) && is_string($_GET['_wpnonce']) ? wp_unslash($_GET['_wpnonce']) : '';
    if (!preg_match('/\A[a-f0-9]{32}\z/', $id)
        || !wp_verify_nonce($nonce, 'staci_download_upload_' . $id)) {
        wp_die('Érvénytelen vagy lejárt letöltési hivatkozás. Frissítse a futás részleteit.', '', array('response' => 403));
    }
    $limited = false;
    $runs = staci_run_index(staci_run_records('/var/log/staci', $limited), $limited);
    $path = isset($runs[$id]) ? staci_run_upload_path($runs[$id]) : false;
    if (!$path) {
        wp_die('A feltöltött fájl vagy a hozzá tartozó napló már nem érhető el.', '', array('response' => 404));
    }
    $stream = @fopen($path, 'rb');
    $opened = $stream ? fstat($stream) : false;
    clearstatcache(true, $path);
    $current = @lstat($path);
    // Use the validated open descriptor for the response; reject replacement
    // between resolving and opening, non-regular files and symlink substitution.
    if (!$opened || !$current || ($current['mode'] & 0170000) !== 0100000
        || ($opened['mode'] & 0170000) !== 0100000
        || $opened['ino'] !== $current['ino'] || $opened['dev'] !== $current['dev']
        || staci_run_upload_path($runs[$id]) !== $path) {
        if ($stream) { fclose($stream); }
        wp_die('A feltöltött fájl nem olvasható. Frissítse a futás részleteit.', '', array('response' => 404));
    }
    return array('stream' => $stream, 'filename' => $runs[$id]['filename'], 'size' => $opened['size']);
}

function staci_run_download_upload() {
    nocache_headers();
    $download = staci_run_prepare_upload_download();
    // A plugin/output buffer must not prepend HTML or compress a binary response.
    while (ob_get_level() > 0) {
        if (!ob_end_clean()) {
            fclose($download['stream']);
            wp_die('A letöltés nem indítható el.', '', array('response' => 500));
        }
    }
    header('Content-Type: application/octet-stream');
    header('Content-Disposition: attachment; filename="' . $download['filename'] . '"');
    header('Content-Length: ' . $download['size']);
    header('X-Content-Type-Options: nosniff');
    header('Cache-Control: private, no-store, no-cache, must-revalidate');
    fpassthru($download['stream']);
    fclose($download['stream']);
    exit;
}

add_action('admin_post_staci_download_upload', 'staci_run_download_upload');
add_action('admin_post_nopriv_staci_download_upload', 'staci_run_download_upload');
