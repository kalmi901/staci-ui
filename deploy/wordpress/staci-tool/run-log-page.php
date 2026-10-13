<?php
/** Admin-only presentation; all log values are untrusted text. */
defined('ABSPATH') || exit;
require_once __DIR__ . '/run-log-data.php';

function staci_run_query($key) {
    return isset($_GET[$key]) && is_string($_GET[$key]) ? sanitize_text_field(wp_unslash($_GET[$key])) : '';
}

function staci_run_page() {
    if (!current_user_can('manage_options')) {
        wp_die('Nincs jogosultságod a napló megtekintéséhez.', '', array('response' => 403));
    }
    nocache_headers();
    $limited = false;
    $runs = staci_run_index(staci_run_records('/var/log/staci', $limited), $limited);
    $base = admin_url('tools.php');
    $selected_id = staci_run_query('execution');
    $q = staci_run_query('q');
    $status = staci_run_query('status');
    $from = staci_run_query('from');
    $to = staci_run_query('to');
    foreach (array('from', 'to') as $field) {
        if (!preg_match('/^\d{4}-\d\d-\d\d$/', $$field)) { $$field = ''; }
    }
    $statuses = staci_run_statuses();
    $filtered = array_filter($runs, function ($run) use ($q, $status, $from, $to) {
        $day = substr(staci_run_local_time($run['utc']), 0, 10);
        $haystack = implode(' ', array(staci_run_user_label($run), $run['user_id'], $run['filename'], $run['model_id'], $run['run_id'], $run['id']));
        return ($q === '' || stripos(remove_accents($haystack), remove_accents($q)) !== false)
            && ($status === '' || $run['status'] === $status)
            && ($from === '' || $day >= $from) && ($to === '' || $day <= $to);
    });
    $page = max(1, min((int) staci_run_query('pagenum'), max(1, (int) ceil(count($filtered) / 50))));
    $args = array('page' => 'staci-tool-logs', 'q' => $q, 'status' => $status,
        'from' => $from, 'to' => $to, 'pagenum' => $page);
    echo '<div class="wrap"><h1>STACI futások</h1><p>Időzóna: Europe/Budapest. '
        . 'A befejezett futás nem feltétlenül jelent numerikusan érvényes eredményt.</p>';
    echo '<p><a class="button" href="' . esc_url(add_query_arg(array('page' => 'staci-tool-logs', 'view' => 'raw'), $base))
        . '">Nyers napló</a></p>';
    echo '<p>Legfeljebb 500 megőrzött futás vagy esemény.</p>';
    if ($limited) { echo '<div class="notice notice-warning"><p>A megjelenített adatok olvasási korlát vagy fájlhozzáférési hiba miatt hiányosak.</p></div>'; }
    echo '<form method="get"><input type="hidden" name="page" value="staci-tool-logs">';
    echo '<p><label>Keresés (név, fájl, azonosító) <input type="search" name="q" value="' . esc_attr($q) . '"></label> ';
    echo '<label>Állapot <select name="status"><option value="">Összes</option>';
    foreach ($statuses as $key => $label) {
        echo '<option value="' . esc_attr($key) . '"' . selected($status, $key, false) . '>' . esc_html($label) . '</option>';
    }
    echo '</select></label> <label>Ettől <input type="date" name="from" value="' . esc_attr($from) . '"></label> '
        . '<label>Eddig <input type="date" name="to" value="' . esc_attr($to) . '"></label> ';
    submit_button('Szűrés / frissítés', 'secondary', 'submit', false);
    echo '</p></form>';
    if ($selected_id !== '') {
        if (!isset($runs[$selected_id])) {
            echo '<div class="notice notice-info"><p>A futás nem található a megőrzött naplóban.</p></div>';
        } else {
            $run = $runs[$selected_id];
            echo '<section style="background:#fff;border:1px solid #c3c4c7;padding:16px;margin:16px 0"><h2>Futás részletei</h2>';
            echo '<p><strong>' . esc_html($run['filename'] ?: 'Ismeretlen fájl') . '</strong> — '
                . esc_html(staci_run_user_label($run)) . ' — ' . esc_html($statuses[$run['status']]) . '</p>';
            echo '<p>Naplóazonosító: <code>' . esc_html($run['id']) . '</code><br>Modellazonosító: <code>'
                . esc_html($run['model_id']) . '</code><br>Futásazonosító: <code>' . esc_html($run['run_id']) . '</code></p>';
            echo '<p>Első rögzített esemény: ' . esc_html(staci_run_local_time($run['utc']))
                . '<br>Befejezés: ' . esc_html(isset($run['ended_utc']) ? staci_run_local_time($run['ended_utc']) : 'Nem áll rendelkezésre') . '</p>';
            if ($run['legacy'] || !$run['started'] || !$run['finished']) {
                echo '<p><strong>Hiányos eseménysor.</strong> A napló nem tartalmaz teljes futástörténetet; a futás aktuális állapota ebből nem határozható meg.</p>';
            }
            if (!empty($run['error'])) {
                echo '<div class="notice notice-error inline"><p>' . esc_html($run['error']) . '</p></div>';
            }
            $prepared = $run['events']['prepared'] ?? array();
            echo '<p>Bemenet ellenőrzőösszege (SHA-256): <code>' . esc_html($prepared['input_sha256'] ?? 'Nem áll rendelkezésre') . '</code></p>';
            echo '<p>A reprodukáláshoz azonos bemenet, paraméterek és programverziók szükségesek. '
                . 'Fájlletöltés ezen a felületen nem érhető el.</p>';
            staci_run_parameters($run);
            echo '<details><summary>Futtatási metaadatok</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:350px;overflow:auto">'
                . esc_html(json_encode($run['events'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE)) . '</pre></details>';
            echo '<details><summary>Napló és hibarészletek</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:500px;overflow:auto">'
                . esc_html($run['raw']) . '</pre></details>';
            if ($run['truncated']) { echo '<p>Csonkolt naplórészlet. További bejegyzések a nyers naplóban érhetők el.</p>'; }
            echo '<h3>Diagnosztikai összefoglaló</h3><textarea id="staci-run-summary" readonly rows="8" style="width:100%">'
                . esc_textarea(staci_run_summary($run)) . '</textarea><p><button type="button" class="button" id="staci-copy-summary">Összefoglaló másolása</button> '
                . '<span id="staci-copy-result" role="status"></span></p></section>';
            echo <<<'HTML'
<script>
document.getElementById('staci-copy-summary').addEventListener('click', async function () {
    const field = document.getElementById('staci-run-summary');
    const result = document.getElementById('staci-copy-result');
    try { await navigator.clipboard.writeText(field.value); result.textContent = 'Másolva.'; }
    catch (_) { field.focus(); field.select(); result.textContent = 'A szöveg kijelölve. Másolás: Ctrl+C vagy ⌘C.'; }
});
</script>
HTML;
        }
    }
    echo '<h2>Futáslista (' . (int) count($filtered) . ')</h2><table class="widefat striped"><thead><tr>';
    foreach (array('Időpont', 'Felhasználó', 'Fájl', 'Számítás', 'Állapot', 'Részletek') as $label) { echo '<th>' . esc_html($label) . '</th>'; }
    echo '</tr></thead><tbody>';
    foreach (array_slice($filtered, ($page - 1) * 50, 50, true) as $id => $run) {
        $type = $run['type'] === 'hydraulic' ? 'Hidraulika' : ($run['type'] === 'partition' ? 'Particionálás' : ($run['type'] === 'flushing' ? 'Öblítés' : 'Ismeretlen'));
        echo '<tr><td>' . esc_html(staci_run_local_time($run['utc'])) . '</td><td>' . esc_html(staci_run_user_label($run))
            . '</td><td>' . esc_html($run['filename'] ?: 'Nem áll rendelkezésre')
            . '</td><td>' . esc_html($type) . '</td><td>' . esc_html($statuses[$run['status']])
            . ($run['legacy'] ? '<br><small>Korábbi, önálló esemény</small>' : '') . '</td><td><a href="'
            . esc_url(add_query_arg($args + array('execution' => $id), $base)) . '">Megnyitás</a></td></tr>';
    }
    if (!$filtered) { echo '<tr><td colspan="6">Nincs a szűrésnek megfelelő bejegyzés.</td></tr>'; }
    echo '</tbody></table><p>';
    if ($page > 1) { echo '<a class="button" href="' . esc_url(add_query_arg(array_merge($args, array('pagenum' => $page - 1)), $base)) . '">Előző</a> '; }
    echo (int) $page . ' / ' . max(1, (int) ceil(count($filtered) / 50));
    if ($page * 50 < count($filtered)) { echo ' <a class="button" href="' . esc_url(add_query_arg(array_merge($args, array('pagenum' => $page + 1)), $base)) . '">Következő</a>'; }
    echo '</p></div>';
}

function staci_run_parameters($run) {
    $events = $run['events'];
    $requested = $events['started']['settings'] ?? array();
    $labels = array('backend' => 'Szolver', 'override_enabled' => 'Időbeállítások felülírása',
        'duration' => 'Kért időtartam (óra)', 'hydraulic_timestep' => 'Kért időlépés (perc)',
        'n_comm' => 'Közösségek száma', 'obj_type' => 'Célfüggvény', 'weight_type' => 'Súlyozás',
        'hydrant_text' => 'Öblítési csomópontok', 'mode' => 'Öblítési mód',
        'hydrant_area' => 'Kifolyási keresztmetszet (m²)', 'loss_coefficient' => 'Veszteségtényező',
        'velocity_threshold' => 'Sebességküszöb (m/s)', 'min_pressure_head' => 'Minimális nyomásmagasság (m)',
        'write_networks' => 'Hálózati fájlok mentése', 'weight_type_mod' => 'Súlyozási mód', 'popsize' => 'Populációméret', 'ngen' => 'Generációk száma',
        'pmut' => 'Mutáció valószínűsége', 'pcross' => 'Keresztezés valószínűsége', 'seed' => 'Véletlenszám-generátor kezdőértéke');
    echo '<h3>Beállítások</h3><table class="widefat striped"><tbody>';
    foreach ($requested as $key => $value) {
        if (($key === 'duration' || $key === 'hydraulic_timestep') && empty($requested['override_enabled'])) { continue; }
        if (is_bool($value)) { $value = $value ? 'Igen' : 'Nem'; }
        elseif (!is_scalar($value)) { $value = json_encode($value); }
        echo '<tr><th scope="row">' . esc_html($labels[$key] ?? $key) . '</th><td>' . esc_html($value) . '</td></tr>';
    }
    $effective = $events['prepared']['effective_options'] ?? array();
    $effective_labels = array('duration' => 'Tényleges időtartam (másodperc)',
        'hydraulic_timestep' => 'Tényleges hidraulikai időlépés (másodperc)',
        'rule_timestep' => 'Szabály-időlépés (másodperc)', 'report_timestep' => 'Eredményrögzítési időlépés (másodperc)',
        'demand_multiplier' => 'Fogyasztási szorzó');
    foreach ($effective as $key => $value) {
        echo '<tr><th scope="row">' . esc_html($effective_labels[$key] ?? $key) . '</th><td>' . esc_html(is_scalar($value) ? $value : json_encode($value)) . '</td></tr>';
    }
    if (!$requested && !$effective) { echo '<tr><td>Nincsenek rögzített paraméterek.</td></tr>'; }
    if (isset($events['finished']['elapsed_seconds'])) {
        echo '<tr><th scope="row">Eltelt idő (másodperc)</th><td>' . esc_html($events['finished']['elapsed_seconds']) . '</td></tr>';
    }
    echo '</tbody></table>';
}
