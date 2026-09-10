<?php
/**
 * Plugin Name: STACI Tool
 * Description: Embeds STACI and verifies WordPress sessions for the reverse proxy.
 * Version: 1.0.0
 */

defined('ABSPATH') || exit;

function staci_tool_access() {
    nocache_headers();
    $cookie = wp_parse_auth_cookie('', 'logged_in');
    if (!$cookie || (int) $cookie['expiration'] <= time() || !wp_validate_auth_cookie('', 'logged_in')) {
        status_header(401);
        exit('Please sign in to WordPress and reload the tool page.');
    }

    $method = $_SERVER['HTTP_X_FORWARDED_METHOD'] ?? '';
    if (!in_array($method, array('GET', 'HEAD', 'POST'), true)) {
        status_header(403);
        exit('Unsupported request method.');
    }

    if ($method === 'POST') {
        $home = wp_parse_url(home_url('/'));
        $expected_origin = $home['scheme'] . '://' . $home['host'];
        if (isset($home['port'])) {
            $expected_origin .= ':' . $home['port'];
        }
        $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
        if ($origin !== $expected_origin) {
            status_header(403);
            exit('Invalid request origin.');
        }
    }

    header('X-Staci-Access: allowed');
    status_header(204);
    exit;
}

add_action('wp_ajax_staci_tool_access', 'staci_tool_access');
add_action('wp_ajax_nopriv_staci_tool_access', 'staci_tool_access');

function staci_tool_shortcode() {
    if (!is_user_logged_in()) {
        return '<p><a href="' . esc_url(wp_login_url(get_permalink())) . '">Bejelentkezés a tool használatához</a></p>';
    }

    return '<iframe src="' . esc_url(home_url('/staci-app/')) . '" title="STACI" style="display:block;width:100%;height:85vh;min-height:600px;border:0;"></iframe>';
}

add_shortcode('staci_tool', 'staci_tool_shortcode');
