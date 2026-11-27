<?php
/** Download stored solver inputs and metadata for one explicitly logged run. */
defined('ABSPATH') || exit;

function staci_run_file_specs($run) {
    $type = $run['type'] ?? '';
    $id = $run['run_id'] ?? '';
    if (!empty($run['legacy']) || empty($run['started'])
        || !in_array($type, array('hydraulic', 'partition', 'flushing'), true)
        || !is_string($id) || !preg_match('/\A[a-f0-9]{12}\z/', $id)) {
        return array();
    }
    $events = $run['events'] ?? array();
    $allocated = $events['allocated']['run_id'] ?? '';
    $prepared = $events['prepared']['run_id'] ?? '';
    // A finish alone does not establish which directory was used as input.
    if ($allocated === '' && $prepared === '') { return array(); }
    foreach (array($allocated, $prepared, $events['finished']['run_id'] ?? '') as $event_id) {
        if ($event_id !== '' && $event_id !== $id) { return array(); }
    }
    $files = array('inp' => array('name' => $type === 'hydraulic' ? 'input.inp' : 'model.inp',
        'label' => 'Futtatott INP letöltése'));
    if ($type === 'hydraulic') {
        $backend = $events['started']['settings']['backend'] ?? '';
        if ($backend === 'staci') {
            $files['parameters'] = array('name' => 'results.meta.json', 'label' => 'Futási metaadatok (JSON)');
        } elseif ($backend === 'wntr') {
            $files['parameters'] = array('name' => 'run.json', 'label' => 'Futásleíró (JSON)');
        }
    } elseif ($type === 'partition') {
        $files['parameters'] = array('name' => 'staci_split_settings.xml', 'label' => 'Particionálási beállítások (XML)');
    } else {
        $files['parameters'] = array('name' => 'flushing_config.json', 'label' => 'Öblítési beállítások (JSON)');
    }
    return $files;
}

function staci_run_file_path($run, $file) {
    $specs = staci_run_file_specs($run);
    if (!isset($specs[$file])) { return false; }
    // All directory identifiers come from the selected log, and filenames are
    // fixed here. Never accept paths, backend names or run IDs from the URL.
    $root = '/var/lib/staci-data/runs';
    $type_dir = $root . '/' . $run['type'];
    $directory = $type_dir . '/' . $run['run_id'];
    $path = $directory . '/' . $specs[$file]['name'];
    clearstatcache(true);
    foreach (array($root, $type_dir, $directory, $path) as $component) {
        if (is_link($component) || realpath($component) !== $component) { return false; }
    }
    return is_file($path) && is_readable($path) ? $path : false;
}

function staci_run_file_url($id, $file) {
    return wp_nonce_url(add_query_arg(array('action' => 'staci_download_run_file',
        'execution' => $id, 'file' => $file), admin_url('admin-post.php')),
        'staci_download_run_file_' . $id . '_' . $file);
}

function staci_run_prepare_file_download() {
    if (!current_user_can('manage_options')) {
        wp_die('Nincs jogosultságod a fájl letöltéséhez.', '', array('response' => 403));
    }
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
        wp_die('Nem támogatott kérés.', '', array('response' => 405));
    }
    $id = isset($_GET['execution']) && is_string($_GET['execution']) ? wp_unslash($_GET['execution']) : '';
    $file = isset($_GET['file']) && is_string($_GET['file']) ? wp_unslash($_GET['file']) : '';
    $nonce = isset($_GET['_wpnonce']) && is_string($_GET['_wpnonce']) ? wp_unslash($_GET['_wpnonce']) : '';
    if (!preg_match('/\A[a-f0-9]{32}\z/', $id) || !in_array($file, array('inp', 'parameters'), true)
        || !wp_verify_nonce($nonce, 'staci_download_run_file_' . $id . '_' . $file)) {
        wp_die('Érvénytelen vagy lejárt letöltési hivatkozás. Frissítse a futás részleteit.', '', array('response' => 403));
    }
    $limited = false;
    $runs = staci_run_index(staci_run_records('/var/log/staci', $limited), $limited);
    $path = isset($runs[$id]) ? staci_run_file_path($runs[$id], $file) : false;
    if (!$path) {
        wp_die('A futási fájl vagy a hozzá tartozó napló már nem érhető el.', '', array('response' => 404));
    }
    $stream = @fopen($path, 'rb');
    $opened = $stream ? fstat($stream) : false;
    clearstatcache(true, $path);
    $current = @lstat($path);
    // Keep using the validated descriptor, rejecting file/symlink replacement.
    if (!$opened || !$current || ($current['mode'] & 0170000) !== 0100000
        || ($opened['mode'] & 0170000) !== 0100000
        || $opened['ino'] !== $current['ino'] || $opened['dev'] !== $current['dev']
        || staci_run_file_path($runs[$id], $file) !== $path) {
        if ($stream) { fclose($stream); }
        wp_die('A futási fájl nem olvasható. Frissítse a futás részleteit.', '', array('response' => 404));
    }
    $expected = $runs[$id]['events']['prepared']['input_sha256'] ?? '';
    if ($file === 'inp' && is_string($expected) && preg_match('/\A[a-f0-9]{64}\z/', $expected)) {
        $hash = hash_init('sha256');
        hash_update_stream($hash, $stream);
        if (!hash_equals($expected, hash_final($hash)) || !rewind($stream)) {
            fclose($stream);
            wp_die('A mentett INP eltér a naplózott szolverbemenettől.', '', array('response' => 409));
        }
    }
    $specs = staci_run_file_specs($runs[$id]);
    return array('stream' => $stream, 'filename' => $runs[$id]['run_id'] . '-' . $specs[$file]['name'],
        'size' => $opened['size']);
}

function staci_run_download_file() {
    nocache_headers();
    $download = staci_run_prepare_file_download();
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

add_action('admin_post_staci_download_run_file', 'staci_run_download_file');
add_action('admin_post_nopriv_staci_download_run_file', 'staci_run_download_file');
