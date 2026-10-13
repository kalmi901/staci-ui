<?php
/** Bounded, read-only index of application logs. No database or inferred run pairing. */
defined('ABSPATH') || exit;

function staci_run_header($line) {
    $pattern = <<<'REGEX'
~^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}Z) \| ([A-Z]+)\s*\| ([\w.]+) \| (?:execution_id=([a-f0-9]{32}|-) \| )?user_id=([0-9]+|-) user=("(?:[^"\\]|\\.)*"|-) \| (.*)$~
REGEX;
    if (!preg_match($pattern, rtrim($line, "\r\n"), $m)) { return null; }
    return array('utc' => $m[1], 'level' => $m[2], 'logger' => $m[3],
        'id' => $m[4], 'user_id' => $m[5], 'user' => $m[6] === '-' ? '-' : json_decode($m[6], true),
        'message' => $m[7]);
}

function staci_run_records($directory, &$limited) {
    foreach (array_reverse(staci_tool_log_names()) as $name) {
        $path = $directory . '/' . $name;
        $resolved = realpath($path);
        if (is_link($path) || !$resolved || dirname($resolved) !== realpath($directory) || !is_file($resolved)) { continue; }
        $stream = @fopen($resolved, 'rb');
        if (!$stream) { $limited = true; continue; }
        // Snapshot a bounded tail of each file; do not chase a growing log.
        $size = fstat($stream)['size'];
        $start = max(0, $size - 6 * 1024 * 1024);
        fseek($stream, $start);
        if ($start) { fgets($stream, 65537); $limited = true; }
        $record = null;
        while (ftell($stream) < $size && ($line = fgets($stream, 65537)) !== false) {
            $header = staci_run_header($line);
            if ($header) {
                if ($record !== null) { yield $record; }
                $record = $header + array('raw' => $line, 'source' => $name);
            } elseif ($record !== null) {
                $room = max(0, 32768 - strlen($record['raw']));
                $record['raw'] .= substr($line, 0, $room);
                if (strlen($line) > $room) { $limited = true; }
            }
        }
        if ($record !== null) { yield $record; }
        fclose($stream);
    }
}

function staci_run_index($records, &$limited) {
    $runs = array();
    $uploads = array();
    $sequence = 0;
    foreach ($records as $record) {
        $message = $record['message'];
        if (preg_match('/^Model uploaded: model_id=([a-f0-9]{12}) filename=(.*?) size=\d+$/', $message, $m)) {
            $uploads[$m[1]] = $m[2];
            if (count($uploads) > 1000) { array_shift($uploads); }
        }
        $id = $record['id'];
        $legacy = !$id || $id === '-';
        if ($legacy) {
            // Older records lack a request ID: never join overlapping starts/ends by guesswork.
            if (!preg_match('/^(Hydraulic simulation|Network partitioning) (started|finished|failed):/', $message, $m)) { continue; }
            $id = 'legacy-' . (++$sequence);
            $kind = $m[1] === 'Hydraulic simulation' ? 'hydraulic' : 'partition';
            $old_event = $m[2];
        }
        if (!isset($runs[$id])) {
            $runs[$id] = array('id' => $id, 'utc' => $record['utc'], 'user' => $record['user'],
                'user_id' => $record['user_id'], 'status' => 'incomplete', 'type' => '',
                'model_id' => '', 'filename' => '', 'run_id' => '', 'events' => array(),
                'raw' => '', 'truncated' => false, 'started' => false, 'finished' => false,
                'legacy' => $legacy);
        }
        $run =& $runs[$id];
        $remaining = max(0, 24576 - strlen($run['raw']));
        $run['raw'] .= substr($record['raw'], 0, $remaining);
        if (strlen($record['raw']) > $remaining) { $run['truncated'] = true; }
        if ($record['level'] === 'ERROR' || $record['level'] === 'CRITICAL') {
            $error_lines = explode("\n", trim($record['raw']));
            $run['error'] = substr(end($error_lines), 0, 2048);
        }
        if ($legacy) {
            $run['type'] = $kind;
            $run['status'] = $old_event === 'failed' ? 'failed' : ($old_event === 'finished' ? 'completed' : 'incomplete');
            if (preg_match('/model_id=([a-f0-9]{12})/', $message, $m)) { $run['model_id'] = $m[1]; }
            if (preg_match('/run_id=([a-f0-9]{12})/', $message, $m)) { $run['run_id'] = $m[1]; }
            $run['filename'] = $uploads[$run['model_id']] ?? '';
        } elseif ($record['logger'] === 'src.run_logging' && str_starts_with($message, 'STACI_RUN ')) {
            if (strlen($message) > 16384) { $run['truncated'] = true; }
            $event = strlen($message) > 16384 ? null : json_decode(substr($message, 10), true, 16);
            if (is_array($event) && ($event['schema'] ?? null) === 1 && ($event['execution_id'] ?? null) === $id
                && in_array($event['event'] ?? '', array('started', 'environment', 'allocated', 'prepared', 'finished'), true)) {
                $run['events'][$event['event']] = $event;
                if ($event['event'] === 'started') {
                    $run['started'] = true;
                    $run['utc'] = $record['utc'];
                    $run['type'] = is_string($event['run_type'] ?? null) ? $event['run_type'] : '';
                    $run['model_id'] = is_string($event['model_id'] ?? null) ? $event['model_id'] : '';
                    $run['filename'] = is_string($event['filename'] ?? null) ? $event['filename'] : '';
                }
                if (!empty($event['run_id']) && is_string($event['run_id'])) { $run['run_id'] = $event['run_id']; }
                if ($event['event'] === 'finished') {
                    $run['finished'] = true;
                    $run['ended_utc'] = $record['utc'];
                    $run['status'] = in_array($event['status'] ?? '', array('failed', 'completed', 'completed_with_warnings'), true)
                        ? $event['status'] : 'incomplete';
                }
            }
        }
        unset($run);
        if (count($runs) > 500) { array_shift($runs); $limited = true; }
    }
    foreach ($runs as &$run) {
        if (!$run['legacy'] && (!$run['started'] || !$run['finished'])) { $run['status'] = 'incomplete'; }
    }
    unset($run);
    uasort($runs, function ($a, $b) { return strcmp($b['utc'], $a['utc']); });
    return $runs;
}

function staci_run_local_time($utc) {
    $date = DateTimeImmutable::createFromFormat('Y-m-d H:i:s,v\Z', $utc, new DateTimeZone('UTC'));
    return $date ? $date->setTimezone(new DateTimeZone('Europe/Budapest'))->format('Y-m-d H:i:s T') : $utc;
}

function staci_run_statuses() {
    return array('completed' => 'Befejeződött', 'completed_with_warnings' => 'Befejeződött, figyelmeztetéssel',
        'failed' => 'Hiba', 'incomplete' => 'Hiányos napló');
}

function staci_run_user_label($run) {
    if (empty($run['user_id']) || $run['user_id'] === '-') { return 'Nem rögzített'; }
    $name = !empty($run['user']) && $run['user'] !== '-' ? $run['user'] : 'Név nem rögzített';
    return $name . ' (ID: ' . $run['user_id'] . ')';
}

function staci_run_summary($run) {
    return 'STACI diagnosztikai összefoglaló' . "\n"
        . 'Naplóazonosító: ' . $run['id'] . "\n"
        . 'Időpont: ' . staci_run_local_time($run['utc']) . ' / UTC: ' . $run['utc'] . "\n"
        . 'Felhasználó: ' . staci_run_user_label($run) . "\n"
        . 'Fájl: ' . ($run['filename'] ?: 'Nem áll rendelkezésre') . "\n"
        . 'Modell: ' . $run['model_id'] . ' / Futás: ' . $run['run_id'] . "\n"
        . 'Állapot: ' . (staci_run_statuses()[$run['status']] ?? 'Ismeretlen') . "\n"
        . ($run['legacy'] ? 'Korábbi, önálló esemény; a futástörténet hiányos.' . "\n" : '')
        . 'A befejezett futás nem feltétlenül jelent numerikusan érvényes eredményt.' . "\n"
        . 'Futtatási adatok:' . "\n" . json_encode($run['events'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE)
        . "\n\nNapló:\n" . $run['raw']
        . ($run['truncated'] ? "\n[A részlet méretkorlát miatt csonkolva.]" : '');
}
