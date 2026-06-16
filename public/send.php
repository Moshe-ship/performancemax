<?php
/**
 * Performance MAX Agency — form handler.
 *
 * Receives the contact form and the home-page "free audit" lead form,
 * then emails the lead to info@performancemaxagency.com through the
 * agency's own Google Workspace over authenticated SMTP (so SPF/DKIM
 * pass and the message lands in the inbox, not spam).
 *
 * Credentials are NOT stored here. They live in mail_secrets.php, which
 * the GitHub Actions deploy writes from repository secrets on every push.
 */

header('Content-Type: application/json; charset=utf-8');

// --- Only accept POST ---
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'error' => 'Method not allowed']);
    exit;
}

// --- Honeypot: bots fill hidden fields, humans don't ---
if (!empty($_POST['company_website'] ?? '')) {
    // Pretend success so the bot moves on.
    echo json_encode(['success' => true]);
    exit;
}

// --- Helpers ---
function field(string $key, int $max = 2000): string {
    $v = trim((string) ($_POST[$key] ?? ''));
    $v = str_replace(["\r", "\n", "\0"], [' ', ' ', ''], substr($v, 0, $max));
    return $v;
}
function multiline(string $key, int $max = 5000): string {
    return trim(substr((string) ($_POST[$key] ?? ''), 0, $max));
}

$name     = field('name', 120);
$email    = field('email', 200);
$phone    = field('phone', 60);
$business = field('business', 200);
$website  = field('website', 300);
$service  = field('service', 120);
$location = field('location', 160);
$message  = multiline('message');
$source   = field('source', 60) ?: 'website';

// --- Validate ---
$errors = [];
if ($name === '')                                   $errors[] = 'name';
if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) $errors[] = 'email';

if ($errors) {
    http_response_code(422);
    echo json_encode(['success' => false, 'error' => 'Please enter your name and a valid email.', 'fields' => $errors]);
    exit;
}

// --- Load credentials (written at deploy time from GitHub secrets) ---
$secretsFile = __DIR__ . '/mail_secrets.php';
if (!is_file($secretsFile)) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Mail is not configured yet. Please email info@performancemaxagency.com directly.']);
    exit;
}
$cfg = require $secretsFile; // ['user' => ..., 'pass' => ..., 'to' => ...]

require __DIR__ . '/vendor/PHPMailer/Exception.php';
require __DIR__ . '/vendor/PHPMailer/PHPMailer.php';
require __DIR__ . '/vendor/PHPMailer/SMTP.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

// --- Build the email body ---
$rows = [
    'Name'          => $name,
    'Email'         => $email,
    'Phone'         => $phone,
    'Business'      => $business,
    'Website'       => $website,
    'Service'       => $service,
    'City / ZIP'    => $location,
    'Source'        => $source,
];
$lines = [];
foreach ($rows as $label => $val) {
    if ($val !== '') {
        $lines[] = $label . ': ' . $val;
    }
}
if ($message !== '') {
    $lines[] = '';
    $lines[] = 'Message:';
    $lines[] = $message;
}
$body = implode("\n", $lines);

$subjectSource = $source === 'audit' ? 'Free Audit Request' : 'Contact Form';
$subject = "[performancemaxagency.com] {$subjectSource} — {$name}";

// --- Send via Google Workspace SMTP ---
$mail = new PHPMailer(true);
try {
    $mail->isSMTP();
    $mail->Host       = $cfg['host'] ?? 'smtp.gmail.com';
    $mail->SMTPAuth   = true;
    $mail->Username   = $cfg['user'];
    $mail->Password   = $cfg['pass'];
    $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;
    $mail->Port       = (int) ($cfg['port'] ?? 587);
    $mail->CharSet    = 'UTF-8';
    $mail->Timeout    = 15;

    // Authenticated account is the sender; replies go to the lead.
    $mail->setFrom($cfg['user'], 'Performance MAX Website');
    $mail->addAddress($cfg['to'] ?? $cfg['user']);
    $mail->addReplyTo($email, $name);

    $mail->Subject = $subject;
    $mail->Body    = $body;

    $mail->send();
    echo json_encode(['success' => true]);
} catch (Exception $e) {
    http_response_code(502);
    error_log('[send.php] Mail error: ' . $mail->ErrorInfo);
    echo json_encode(['success' => false, 'error' => 'Something went wrong sending your message. Please email info@performancemaxagency.com directly.']);
}
