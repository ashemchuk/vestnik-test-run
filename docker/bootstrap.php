<?php
// Initialize the test configuration once. Preserve changes from the installer.
$path = '/var/www/html/config.inc.php';
$marker = '/var/www/html/.vestnik-configured';
if (file_exists($marker)) {
    exit(0);
}
$config = file_get_contents($path);
if ($config === false) {
    throw new RuntimeException('OJS configuration is missing');
}
$settings = [
    'general' => [
        'app_key' => '"base64:' . base64_encode(random_bytes(32)) . '"',
        'base_url' => '"http://localhost:8080"',
        'time_zone' => '"Asia/Novosibirsk"',
        'allowed_hosts' => "'[\"localhost\", \"127.0.0.1\"]'",
        'enable_beacon' => 'Off',
    ],
    'database' => [
        'driver' => 'mysqli',
        'host' => 'db',
        'username' => 'ojs',
        'password' => '"' . getenv('OJS_DB_PASSWORD') . '"',
        'name' => 'ojs',
    ],
    'files' => ['files_dir' => '/var/www/files'],
    'security' => [
        'salt' => '"' . bin2hex(random_bytes(32)) . '"',
        'api_key_secret' => '"' . bin2hex(random_bytes(32)) . '"',
    ],
    'email' => [
        'default' => 'smtp',
        'smtp' => 'On',
        'smtp_server' => 'mailpit',
        'smtp_port' => '1025',
    ],
];
foreach ($settings as $section => $values) {
    $pattern = '/(^\[' . preg_quote($section, '/') . '\]\s*\n)(.*?)(?=^\[|\z)/ms';
    $config = preg_replace_callback($pattern, function ($matches) use ($values) {
        $body = $matches[2];
        foreach ($values as $key => $value) {
            $line = '/^\h*;?\h*' . preg_quote($key, '/') . '\h*=.*$/m';
            if (preg_match($line, $body)) {
                $body = preg_replace_callback($line, fn() => "$key = $value", $body, 1);
            } else {
                $body .= "\n$key = $value\n";
            }
        }
        return $matches[1] . $body;
    }, $config, 1);
}
if (file_put_contents($path, $config) === false) {
    throw new RuntimeException('Could not save OJS configuration');
}
chown($path, 'www-data');
touch($marker);
echo "Local OJS configuration initialized.\n";
